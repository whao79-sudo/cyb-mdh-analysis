"""
成交量异常检测 + 滚动 Granger 信号
每天输出量价状态、异常信号和实战判断
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import json
from datetime import datetime
from statsmodels.tsa.stattools import grangercausalitytests
import warnings
warnings.filterwarnings('ignore')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cyb_data.db")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "option_pcr.csv")

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM daily ORDER BY date", conn)
    conn.close()
    num_cols = ['open','high','low','close','volume','amount','pe','pb','turnover']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df = df.dropna(subset=['close'])
    return df

def compute_volume_signals(df):
    """
    计算成交量异常信号
    """
    result = df.copy()
    
    # 1. 均线偏离法 - 多个窗口
    for window in [5, 10, 20, 60]:
        ma = result['volume'].rolling(window).mean()
        std = result['volume'].rolling(window).std()
        result[f'vol_ma{window}'] = ma
        result[f'vol_ratio_{window}'] = result['volume'] / ma
        result[f'vol_zscore_{window}'] = (result['volume'] - ma) / std
    
    # 2. 量价背离检测
    result['pct'] = result['close'].pct_change() * 100
    result['vol_ma20'] = result['vol_ma20']
    
    # 量价组合信号
    conditions = [
        (result['vol_ratio_20'] > 1.5) & (result['pct'] > 2),
        (result['vol_ratio_20'] > 1.5) & (result['pct'] < -2),
        (result['vol_ratio_20'] > 2.0),
        (result['vol_ratio_20'] < 0.6),
        (result['vol_ratio_20'] > 1.3) & (result['pct'] < 0.5) & (result['pct'] > -0.5),
        (result['vol_ratio_20'] > 1.3) & (result['pct'] > 3),
        (result['vol_ratio_20'] > 1.3) & (result['pct'] < -3),
    ]
    signals = [
        '🟢 放量上涨', '🔴 放量下跌',
        '⚠️ 异常天量',
        '🔵 极度缩量',
        '🔮 滞涨放量',
        '🚀 突破放量', '💥 恐慌放量'
    ]
    result['vol_signal'] = np.select(conditions, signals, default='-')
    
    return result

def rolling_granger(df, window=252, step=20):
    """
    滚动 Granger 因果检验
    返回最近几次的 p 值趋势
    """
    df['pct_return'] = df['close'].pct_change() * 100
    df['abs_return'] = np.abs(df['pct_return'])
    df['log_volume'] = np.log(df['volume'] + 1)
    df = df.dropna()
    
    max_lag = 6
    results = []
    
    dates = df.index[window:].tolist()
    for i, end_date in enumerate(dates[::step]):
        window_data = df.iloc[i*step:i*step+window]
        data = window_data[['log_volume', 'abs_return']].dropna()
        if len(data) < 100:
            continue
        try:
            gc = grangercausalitytests(data.values, max_lag, verbose=False)
            best_p = min(gc[lag][0]['ssr_chi2test'][1] for lag in range(1, max_lag+1))
            best_lag = min(range(1, max_lag+1), key=lambda l: gc[l][0]['ssr_chi2test'][1])
            results.append({
                'date': end_date.strftime('%Y-%m-%d'),
                'granger_p': round(best_p, 6),
                'best_lag': best_lag,
                'significant': best_p < 0.05
            })
        except:
            continue
    
    return results[-10:]  # 只保留最近 10 期

def full_lag_granger(df, window=252):
    """
    用最近 window 天的数据，输出每个 lag 的 p 值
    """
    df['pct_return'] = df['close'].pct_change() * 100
    df['abs_return'] = np.abs(df['pct_return'])
    df['log_volume'] = np.log(df['volume'] + 1)
    data = df.tail(window)[['log_volume', 'abs_return']].dropna()
    
    max_lag = 10
    try:
        gc = grangercausalitytests(data.values, max_lag, verbose=False)
        lag_results = []
        for lag in range(1, max_lag + 1):
            p = gc[lag][0]['ssr_chi2test'][1]
            lag_results.append({
                'lag': lag,
                'p_value': round(p, 6),
                'significant': p < 0.05
            })
        return lag_results
    except:
        return []

def generate_signal_report(df, granger_trend, full_lag):
    """
    生成每日量价信号报告 Markdown
    """
    df = compute_volume_signals(df)
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    lines = []
    lines.append(f"# 📊 创业板量价信号日报\n")
    lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    lines.append(f"*数据截至: {latest.name.strftime('%Y-%m-%d')}*\n\n")
    
    # ===== 全周期历史概况 =====
    first_date = df.index[0].strftime('%Y-%m-%d')
    last_date = df.index[-1].strftime('%Y-%m-%d')
    total_days = len(df)
    avg_vol = df['volume'].mean() / 1e8
    max_vol = df['volume'].max() / 1e8
    max_vol_date = df['volume'].idxmax().strftime('%Y-%m-%d')
    min_vol = df['volume'].min() / 1e8
    min_vol_date = df['volume'].idxmin().strftime('%Y-%m-%d')
    vol_90p = df['volume'].quantile(0.9) / 1e8
    vol_10p = df['volume'].quantile(0.1) / 1e8
    
    # 缩量极值 vs 放量极值
    extremes = []
    for window in [5, 20, 60]:
        ratio = df[f'vol_ratio_{window}']
        max_r = ratio.max()
        max_r_date = ratio.idxmax().strftime('%Y-%m-%d')
        min_r = ratio.min()
        min_r_date = ratio.idxmin().strftime('%Y-%m-%d')
        over_2x = (ratio > 2.0).sum()
        under_half = (ratio < 0.5).sum()
        extremes.append(f"  {window}日均: 量比最高 {max_r:.2f}x（{max_r_date}），最低 {min_r:.2f}x（{min_r_date}），"
                        f"超2x={over_2x}次，不足半量={under_half}次")
    
    # 全历史近期对比
    recent_252 = df.tail(252)['volume'].mean() / 1e8
    recent_60 = df.tail(60)['volume'].mean() / 1e8
    
    lines.append("## 全周期量价概况\n")
    lines.append(f"| 指标 | 数值 |\n")
    lines.append(f"|------|------|\n")
    lines.append(f"| 数据范围 | {first_date} ~ {last_date}（{total_days} 个交易日） |\n")
    lines.append(f"| 日均成交量 | {avg_vol:.1f}亿 |\n")
    lines.append(f"| 近1年（252日）均量 | {recent_252:.1f}亿 |\n")
    lines.append(f"| 近3月（60日）均量 | {recent_60:.1f}亿 |\n")
    lines.append(f"| 历史最大成交量 | {max_vol:.1f}亿（{max_vol_date}） |\n")
    lines.append(f"| 历史最小成交量 | {min_vol:.1f}亿（{min_vol_date}） |\n")
    lines.append(f"| 90分位成交量 | {vol_90p:.1f}亿 |\n")
    lines.append(f"| 10分位成交量 | {vol_10p:.1f}亿 |\n\n")
    
    lines.append("### 各周期量比极值\n\n")
    for e in extremes:
        lines.append(f"{e}\n")
    lines.append("\n")
    
    # 今日概况
    vol_billion = latest['volume'] / 1e8
    ma20 = latest.get('vol_ma20', 0) / 1e8
    vol_ratio = latest.get('vol_ratio_20', 0)
    pct = latest.get('pct', 0)
    close = latest['close']
    
    lines.append("## 今日量价概况\n")
    lines.append(f"| 指标 | 数值 |\n")
    lines.append(f"|------|------|\n")
    lines.append(f"| 收盘价 | {close:.2f} |\n")
    lines.append(f"| 日涨跌 | {pct:+.2f}% |\n")
    lines.append(f"| 成交量 | {vol_billion:.1f}亿 |\n")
    lines.append(f"| 20日均量 | {ma20:.1f}亿 |\n")
    lines.append(f"| 量比（vs 20日均量） | {vol_ratio:.2f}x |\n")
    lines.append(f"| 量比（vs 5日均量） | {latest.get('vol_ratio_5', 0):.2f}x |\n")
    lines.append(f"| Z-score（20日） | {latest.get('vol_zscore_20', 0):.2f} |\n")
    lines.append(f"| 量价信号 | {latest.get('vol_signal', '-')} |\n\n")
    
    # 成交量趋势
    lines.append("## 成交量异常检测（多窗口）\n")
    lines.append("| 窗口 | 均量(亿) | 量比 | Z-score | 判断 |\n")
    lines.append("|------|---------|------|---------|------|\n")
    for w in [5, 10, 20, 60]:
        ma = latest.get(f'vol_ma{w}', 0) / 1e8
        ratio = latest.get(f'vol_ratio_{w}', 0)
        z = latest.get(f'vol_zscore_{w}', 0)
        if w == 20:
            judge = latest.get('vol_signal', '-')
        elif ratio > 1.5:
            judge = '异常放量'
        elif ratio < 0.7:
            judge = '明显缩量'
        else:
            judge = '正常范围'
        lines.append(f"| {w}日 | {ma:.1f} | {ratio:.2f}x | {z:+.2f} | {judge} |\n")
    lines.append("\n")
    
    # Granger 因果趋势
    lines.append("## 滚动 Granger 因果趋势\n")
    lines.append("> 成交量 → 波动率（绝对收益）\n\n")
    lines.append("| 窗口结束日 | p值 | 最优滞后 | 显著？ |\n")
    lines.append("|-----------|------|---------|-------|\n")
    if granger_trend:
        for g in reversed(granger_trend[-5:]):
            sig = '✅ 显著' if g['significant'] else '❌'
            # 根据 p 值加颜色指示
            p = g['granger_p']
            if p < 0.01:
                level = '🟢 强烈'
            elif p < 0.05:
                level = '🟡 一般'
            elif p < 0.1:
                level = '🟠 弱'
            else:
                level = '🔴 无'
            lines.append(f"| {g['date']} | {p:.6f} | lag={g['best_lag']} | {sig} ({level}) |\n")
    
    lines.append("\n")
    
    # 全滞后细节
    if full_lag:
        lines.append("## 全滞后 Granger 检验（最近 252 天）\n")
        lines.append("| 滞后天数 | p值 | 显著？ |\n")
        lines.append("|---------|------|-------|\n")
        for lr in full_lag:
            sig = '✅ 显著' if lr['significant'] else '❌'
            lines.append(f"| {lr['lag']}日 | {lr['p_value']:.6f} | {sig} |\n")
        lines.append("\n")
    
    # 综合信号
    lines.append("## 综合信号\n\n")
    signals = []
    
    # 量比信号
    if vol_ratio > 2:
        signals.append("🟢 **异常放量**: 成交量超过 20 日均量 2 倍，关注变盘")
    elif vol_ratio > 1.5:
        signals.append("🟡 **明显放量**: 成交量超过 20 日均量 50%")
    elif vol_ratio < 0.6:
        signals.append("🔵 **极度缩量**: 成交量仅为 20 日均量 60%以下，变盘前兆")
    elif vol_ratio < 0.8:
        signals.append("🔵 **缩量**: 成交量低于 20 日均量 20%")
    
    # Granger 信号
    if granger_trend:
        latest_g = granger_trend[-1]
        if latest_g['significant']:
            if latest_g['granger_p'] < 0.01:
                signals.append("🟢 **Granger 信号强烈**: 成交量对未来波动预测力极强 (p<0.01)")
            else:
                signals.append("🟡 **Granger 信号有效**: 成交量包含波动率预测信息 (p<0.05)")
        else:
            if latest_g['granger_p'] < 0.1:
                signals.append("🟠 **Granger 信号较弱**: 成交量预测力边缘显著 (p<0.1)")
            else:
                signals.append("🔴 **无 Granger 信号**: 成交量对波动率预测力不明显")
    
    # 近3日量比趋势
    recent_ratios = df['vol_ratio_20'].dropna().tail(3).values
    if len(recent_ratios) >= 2:
        if all(r > 1.0 for r in recent_ratios) and recent_ratios[-1] > recent_ratios[0]:
            signals.append("🔥 **量能持续放大**: 连续放量，趋势可能是真突破")
        elif all(r < 1.0 for r in recent_ratios) and recent_ratios[-1] < recent_ratios[0]:
            signals.append("❄️ **量能持续萎缩**: 连续缩量，市场交投清淡")
        elif recent_ratios[0] < 0.8 and recent_ratios[-1] > 1.2:
            signals.append("⚡ **量能突然回升**: 从缩量到放量，可能出现方向选择")
    
    if not signals:
        signals.append("- 今日无显著量价异常信号")
    
    lines.append(f"共 {len(signals)} 条信号:\n")
    for s in signals:
        lines.append(f"- {s}\n")
    
    # PCR 数据段落
    lines.append(pcr_report_section())
    
    lines.append("\n---\n")
    lines.append("*免责：本信号基于统计模型，不构成投资建议*\n")
    
    return "".join(lines)

def load_latest_pcr():
    """从 CSV 加载最新的 PCR 数据"""
    try:
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
            if len(df) > 0:
                latest = df.iloc[-1]
                return latest.to_dict() if isinstance(latest, pd.Series) else latest
    except:
        pass
    return None

def pcr_report_section():
    """生成 PCR 数据报告段落"""
    pcr = load_latest_pcr()
    if not pcr:
        return ""
    
    lines = []
    lines.append("\n## 期权 PCR 数据\n")
    lines.append(f"*数据来源: 深交所 创业板ETF(159915)*\n\n")
    lines.append(f"| 指标 | 数值 |\n")
    lines.append(f"|------|------|\n")
    lines.append(f"| 日期 | {pcr.get('date', '-')} |\n")
    lines.append(f"| 认购成交量 | {int(pcr.get('call_vol', 0)):,} 张 |\n")
    lines.append(f"| 认沽成交量 | {int(pcr.get('put_vol', 0)):,} 张 |\n")
    lines.append(f"| PCR(成交量) | {float(pcr.get('vol_pcr', 0)):.3f} |\n")
    lines.append(f"| 认购未平仓 | {int(pcr.get('call_oi', 0)):,} 张 |\n")
    lines.append(f"| 认沽未平仓 | {int(pcr.get('put_oi', 0)):,} 张 |\n")
    lines.append(f"| PCR(持仓) | {float(pcr.get('oi_pcr', 0)):.3f} |\n")
    
    # 简单信号
    vol_pcr = float(pcr.get('vol_pcr', 0))
    oi_pcr = float(pcr.get('oi_pcr', 0))
    
    vol_signal = ""
    if vol_pcr > 1.0:
        vol_signal = "认沽>认购，情绪偏空"
    elif vol_pcr > 0.85:
        vol_signal = "认沽略多，中性偏空"
    elif vol_pcr > 0.7:
        vol_signal = "认购偏多，情绪中性"
    else:
        vol_signal = "认购明显偏多，情绪乐观"
    
    oi_signal = ""
    if oi_pcr > 1.2:
        oi_signal = "⚠️ 持仓PCR极高，市场对冲需求旺盛"
    elif oi_pcr > 1.0:
        oi_signal = "持仓PCR超过1.0，多头开始对冲"
    elif oi_pcr > 0.8:
        oi_signal = "持仓PCR中性略偏多"
    else:
        oi_signal = "持仓PCR低位，市场偏多"
    
    lines.append(f"\n### PCR 信号判断\n")
    lines.append(f"- **成交量PCR**: {vol_signal}\n")
    lines.append(f"- **持仓量PCR**: {oi_signal}\n")
    
    lines.append("\n")
    return "".join(lines)

def main():
    print("📊 创业板量价信号报告")
    print("="*50)
    
    df = load_data()
    print(f"数据量: {len(df)} 条 ({df.index.min().strftime('%Y-%m-%d')} ~ {df.index.max().strftime('%Y-%m-%d')})")
    
    # 滚动 Granger
    print("\n➡️ 计算滚动 Granger 因果...")
    granger_trend = rolling_granger(df)
    print(f"   最近窗口: {granger_trend[-1] if granger_trend else '空'}")
    
    # 全滞后
    print("\n➡️ 全滞后 Granger 检验...")
    full_lag = full_lag_granger(df)
    print(f"   最优 lag: {min(full_lag, key=lambda x: x['p_value']) if full_lag else 'N/A'}")
    
    # 生成报告
    print("\n➡️ 生成信号报告...")
    report = generate_signal_report(df, granger_trend, full_lag)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "volume_signal.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ 信号报告已保存: {report_path}")

if __name__ == "__main__":
    main()
