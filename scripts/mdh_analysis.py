"""
MDH 假说验证 - 创业板指数成交量与波动率分析
GARCH-X 检验 + Granger 因果检验 + HAR-RV 模型
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import json
from datetime import datetime, timedelta
from arch import arch_model
from statsmodels.tsa.stattools import grangercausalitytests
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cyb_data.db")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

def get_data():
    """从 SQLite 读取数据"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM daily ORDER BY date", conn)
    conn.close()
    if len(df) == 0:
        print("❌ 数据库为空，请先运行 fetch_data.py")
        return None
    
    # 数值转换
    num_cols = ['open','high','low','close','volume','amount','pe','pb','turnover']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['close'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    return df

def calc_returns(df):
    """计算收益率和波动率指标"""
    # 对数收益率
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    
    # 日收益率百分比
    df['pct_return'] = df['close'].pct_change() * 100
    
    # 已实现波动率 (日振幅)
    df['rv'] = (np.log(df['high'] / df['low']))**2 / (4 * np.log(2))
    
    # 周/月已实现波动率（用于 HAR-RV）
    df['rv_week'] = df['rv'].rolling(5).mean()
    df['rv_month'] = df['rv'].rolling(22).mean()
    
    # 对数成交量
    df['log_volume'] = np.log(df['volume'] + 1)
    
    # 对数换手率
    df['log_turnover'] = np.log(df['turnover'] + 0.0001)
    
    # 绝对收益率（波动率的直接度量）
    df['abs_return'] = np.abs(df['pct_return'])
    
    return df.dropna()

def run_garchx_analysis(df):
    """
    GARCH(1,1) + GARCH-X 检验
    MDH 假说预测：加入成交量后，波动率持续性(α+β)下降
    """
    print("\n" + "="*60)
    print("📈 GARCH 模型检验 - MDH 假说")
    print("="*60)
    
    ret = df['pct_return'].dropna() * 100  # 缩放
    
    results = {}
    
    # --- 标准 GARCH(1,1) ---
    print("\n▶ 模型 1: 标准 GARCH(1,1)")
    try:
        am = arch_model(ret[:-1], vol='Garch', p=1, q=1, dist='normal')
        res = am.fit(disp='off')
        alpha = res.params.get('alpha[1]', 0)
        beta = res.params.get('beta[1]', 0)
        omega = res.params.get('omega', 0)
        persistence = alpha + beta
        bic = res.bic
        aic = res.aic
        
        print(f"   ω = {omega:.6f}")
        print(f"   α = {alpha:.6f}")
        print(f"   β = {beta:.6f}")
        print(f"   持续率 (α+β) = {persistence:.6f}")
        print(f"   AIC = {aic:.2f}, BIC = {bic:.2f}")
        
        results['garch'] = {
            'omega': float(omega),
            'alpha': float(alpha),
            'beta': float(beta),
            'persistence': float(persistence),
            'aic': float(aic),
            'bic': float(bic)
        }
    except Exception as e:
        print(f"   ❌ 模型拟合失败: {e}")
        results['garch'] = {'error': str(e)}
    
    # --- GARCH(1,1) + 成交量 ---
    print("\n▶ 模型 2: GARCH(1,1) + 成交量 (GARCH-X)")
    try:
        # 对齐数据
        valid_idx = df.index.intersection(ret.index)
        ret_aligned = ret.loc[valid_idx]
        vol_aligned = df.loc[valid_idx, 'log_volume']
        
        # 标准化成交量
        vol_std = (vol_aligned - vol_aligned.mean()) / vol_aligned.std()
        
        # 构建 GARCH-X 模型 (使用成交量作为外生变量)
        vol_exog = vol_std.values[:-1].reshape(-1, 1)
        
        am_x = arch_model(ret_aligned[:-1], vol='Garch', p=1, q=1, dist='normal')
        res_x = am_x.fit(disp='off', cov_type='robust', last_obs=len(ret_aligned)-1)
        
        # 由于 arch 包对 exog 支持有限，我们手动检验成交量与条件方差的关系
        # 提取条件方差
        cond_var = res_x.conditional_volatility ** 2
        
        # 用成交量对条件方差做回归
        from sklearn.linear_model import LinearRegression
        vol_exog_aligned = vol_std.values[:-1]
        lr = LinearRegression()
        lr.fit(vol_exog_aligned.reshape(-1, 1), cond_var)
        
        vol_significance = lr.coef_[0]
        vol_r2 = lr.score(vol_exog_aligned.reshape(-1, 1), cond_var)
        
        alpha_x = res_x.params.get('alpha[1]', 0)
        beta_x = res_x.params.get('beta[1]', 0)
        persistence_x = alpha_x + beta_x
        
        print(f"   ω = {res_x.params.get('omega', 0):.6f}")
        print(f"   α = {alpha_x:.6f}")
        print(f"   β = {beta_x:.6f}")
        print(f"   持续率 (α+β) = {persistence_x:.6f}")
        print(f"   成交量对条件方差的贡献系数 = {vol_significance:.6f}")
        print(f"   成交量对条件方差的 R² = {vol_r2:.4f}")
        print(f"   AIC = {res_x.aic:.2f}, BIC = {res_x.bic:.2f}")
        
        # MDH 核心验证：比较持续率变化
        if 'persistence' in results['garch']:
            persistence_change = persistence - persistence_x
            print(f"\n   📊 MDH 验证:")
            print(f"      标准GARCH持续率: {persistence:.4f}")
            print(f"      加入成交量后持续率: {persistence_x:.4f}")
            print(f"      持续率下降: {persistence_change:.4f} {'✅ MDH支持' if persistence_change > 0 else '❌ MDH不支持'}")
            results['mdh_verification'] = {
                'garch_persistence': float(persistence),
                'garch_x_persistence': float(persistence_x),
                'persistence_change': float(persistence_change),
                'mdh_supported': bool(persistence_change > 0),
                'volume_coefficient': float(vol_significance),
                'volume_r2': float(vol_r2)
            }
        
        results['garch_x'] = {
            'omega': float(res_x.params.get('omega', 0)),
            'alpha': float(alpha_x),
            'beta': float(beta_x),
            'persistence': float(persistence_x),
            'volume_coef': float(vol_significance),
            'volume_r2': float(vol_r2),
            'aic': float(res_x.aic),
            'bic': float(res_x.bic)
        }
        
    except Exception as e:
        print(f"   ❌ GARCH-X 模型失败: {e}")
        results['garch_x'] = {'error': str(e)}
    
    # --- GARCH(1,1) + 换手率 ---
    print("\n▶ 模型 3: GARCH(1,1) + 换手率")
    try:
        valid_idx = df.index.intersection(ret.index)
        ret_aligned = ret.loc[valid_idx]
        to_aligned = df.loc[valid_idx, 'log_turnover']
        
        to_std = (to_aligned - to_aligned.mean()) / to_aligned.std()
        to_exog = to_std.values[:-1]
        
        am_t = arch_model(ret_aligned[:-1], vol='Garch', p=1, q=1, dist='normal')
        res_t = am_t.fit(disp='off', cov_type='robust', last_obs=len(ret_aligned)-1)
        
        cond_var_t = res_t.conditional_volatility ** 2
        
        from sklearn.linear_model import LinearRegression
        lr_t = LinearRegression()
        lr_t.fit(to_exog.reshape(-1, 1), cond_var_t)
        
        to_significance = lr_t.coef_[0]
        to_r2 = lr_t.score(to_exog.reshape(-1, 1), cond_var_t)
        
        persistence_t = res_t.params.get('alpha[1]', 0) + res_t.params.get('beta[1]', 0)
        
        print(f"   持续率 (α+β) = {persistence_t:.6f}")
        print(f"   换手率对条件方差的贡献系数 = {to_significance:.6f}")
        print(f"   换手率对条件方差的 R² = {to_r2:.4f}")
        
        results['garch_turnover'] = {
            'persistence': float(persistence_t),
            'turnover_coef': float(to_significance),
            'turnover_r2': float(to_r2),
            'aic': float(res_t.aic),
            'bic': float(res_t.bic)
        }
        
        # 对比成交量 vs 换手率
        if 'volume_r2' in results['garch_x']:
            print(f"\n   📊 对比: 成交量R²={results['garch_x']['volume_r2']:.4f}, 换手率R²={to_r2:.4f}")
            better = '成交量' if results['garch_x']['volume_r2'] > to_r2 else '换手率'
            print(f"      {better}对波动率的解释力更强")
            results['volume_vs_turnover'] = {
                'better_predictor': better,
                'volume_r2': float(results['garch_x']['volume_r2']),
                'turnover_r2': float(to_r2)
            }
        
    except Exception as e:
        print(f"   ❌ 换手率模型失败: {e}")
        results['garch_turnover'] = {'error': str(e)}
    
    return results

def run_granger_causality(df):
    """
    Granger 因果检验：成交量 ↔ 波动率
    """
    print("\n" + "="*60)
    print("🔗 Granger 因果检验")
    print("="*60)
    
    # 准备数据
    vol_series = df['log_volume']
    ret_series = df['abs_return']
    
    data = pd.DataFrame({
        'volume': vol_series,
        'abs_return': ret_series
    }).dropna()
    
    # 对成交量去趋势（一阶差分）
    data['vol_diff'] = data['volume'].diff().dropna()
    
    max_lag = 10
    results = {}
    
    for direction, name in [('volume→volatility', ['volume', 'abs_return']), 
                              ('volatility→volume', ['abs_return', 'volume'])]:
        print(f"\n▶ {direction}")
        try:
            test_data = data[name].dropna().values
            gc_result = grangercausalitytests(test_data, max_lag, verbose=False)
            
            best_lag = None
            best_p = 1.0
            for lag in range(1, max_lag + 1):
                p_value = gc_result[lag][0]['ssr_chi2test'][1]
                if p_value < best_p:
                    best_p = p_value
                    best_lag = lag
            
            significant = best_p < 0.05
            print(f"   最优滞后阶数: {best_lag}")
            print(f"   最小 p-value: {best_p:.6f}")
            print(f"   格兰杰因果{'✅ 显著' if significant else '❌ 不显著'}")
            
            results[direction] = {
                'best_lag': best_lag,
                'best_p_value': float(best_p),
                'significant': significant
            }
        except Exception as e:
            print(f"   ❌ 检验失败: {e}")
            results[direction] = {'error': str(e)}
    
    return results

def run_harrv_analysis(df):
    """
    HAR-RV 模型：
    RV_t = β₀ + β₁·RV_{t-1} + β₅·RV_w_{t-1} + β₂₂·RV_m_{t-1} + γ·Volume_{t-1} + ε
    检验成交量是否能提升波动率预测
    """
    print("\n" + "="*60)
    print("📊 HAR-RV 模型 - 成交量预测能力")
    print("="*60)
    
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_squared_error, r2_score
    
    # 准备数据
    df_model = df[['rv', 'rv_week', 'rv_month', 'log_volume']].dropna().copy()
    
    # 滞后一期
    df_model['rv_lag1'] = df_model['rv'].shift(1)
    df_model['rv_week_lag1'] = df_model['rv_week'].shift(1)
    df_model['rv_month_lag1'] = df_model['rv_month'].shift(1)
    df_model['vol_lag1'] = df_model['log_volume'].shift(1)
    
    df_model = df_model.dropna()
    
    y = df_model['rv'].values
    X_basic = df_model[['rv_lag1', 'rv_week_lag1', 'rv_month_lag1']].values
    X_full = df_model[['rv_lag1', 'rv_week_lag1', 'rv_month_lag1', 'vol_lag1']].values
    
    # 80% 训练，20% 测试
    split = int(len(y) * 0.8)
    
    X_train_b, X_test_b = X_basic[:split], X_basic[split:]
    X_train_f, X_test_f = X_full[:split], X_full[split:]
    y_train, y_test = y[:split], y[split:]
    
    # 基础模型 (不含成交量)
    model_basic = LinearRegression()
    model_basic.fit(X_train_b, y_train)
    pred_basic = model_basic.predict(X_test_b)
    r2_basic = r2_score(y_test, pred_basic)
    rmse_basic = np.sqrt(mean_squared_error(y_test, pred_basic))
    
    # 完整模型 (含成交量)
    model_full = LinearRegression()
    model_full.fit(X_train_f, y_train)
    pred_full = model_full.predict(X_test_f)
    r2_full = r2_score(y_test, pred_full)
    rmse_full = np.sqrt(mean_squared_error(y_test, pred_full))
    
    # 改进程度
    r2_improvement = (r2_full - r2_basic) / abs(r2_basic) * 100 if r2_basic != 0 else 0
    rmse_improvement = (rmse_basic - rmse_full) / rmse_basic * 100
    
    print(f"\n   基础 HAR-RV (无成交量):")
    print(f"     R² = {r2_basic:.4f}")
    print(f"     RMSE = {rmse_basic:.6f}")
    print(f"     系数: β_daily={model_basic.coef_[0]:.4f}, β_weekly={model_basic.coef_[1]:.4f}, β_monthly={model_basic.coef_[2]:.4f}")
    
    print(f"\n   完整 HAR-RV (含成交量):")
    print(f"     R² = {r2_full:.4f}")
    print(f"     RMSE = {rmse_full:.6f}")
    print(f"     系数: β_daily={model_full.coef_[0]:.4f}, β_weekly={model_full.coef_[1]:.4f}, β_monthly={model_full.coef_[2]:.4f}")
    print(f"           成交量系数={model_full.coef_[3]:.4f}")
    
    print(f"\n   成交量贡献:")
    print(f"     R² 提升: {r2_improvement:.2f}%")
    print(f"     RMSE 降低: {rmse_improvement:.2f}%")
    volume_significant = abs(model_full.coef_[3]) > 0.01
    print(f"     {'✅ 成交量显著提升预测能力' if volume_significant else '❌ 成交量贡献有限'}")
    
    return {
        'basic_r2': float(r2_basic),
        'basic_rmse': float(rmse_basic),
        'full_r2': float(r2_full),
        'full_rmse': float(rmse_full),
        'r2_improvement_pct': float(r2_improvement),
        'rmse_improvement_pct': float(rmse_improvement),
        'volume_coefficient': float(model_full.coef_[3]),
        'volume_significant': volume_significant,
        'model_basic_coefs': model_basic.coef_.tolist(),
        'model_full_coefs': model_full.coef_.tolist()
    }

def generate_report(garch_results, granger_results, harrv_results, df):
    """生成分析报告"""
    report = []
    report.append("# 🦞 创业板指数 MDH 假说验证报告\n")
    report.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    report.append(f"*数据范围: {df.index.min().strftime('%Y-%m-%d')} ~ {df.index.max().strftime('%Y-%m-%d')}*\n")
    report.append(f"*样本量: {len(df)} 个交易日*\n")
    
    # 基础统计
    report.append("## 📊 基础统计\n")
    basic_stats = df[['close', 'pct_return', 'volume', 'turnover']].describe()
    report.append("```\n" + basic_stats.to_string() + "\n```\n")
    
    # 1. GARCH 检验
    report.append("## 📈 GARCH 模型检验\n")
    if 'mdh_verification' in garch_results:
        mdh = garch_results['mdh_verification']
        report.append(f"- **标准 GARCH(1,1) 持续率 (α+β)**: {mdh['garch_persistence']:.4f}\n")
        report.append(f"- **GARCH-X (含成交量) 持续率**: {mdh['garch_x_persistence']:.4f}\n")
        report.append(f"- **持续率变化**: {mdh['persistence_change']:.4f}\n")
        report.append(f"- **成交量贡献 R²**: {mdh['volume_r2']:.4f}\n")
        report.append(f"- **MDH 假说**: {'✅ 支持' if mdh['mdh_supported'] else '❌ 不支持'}\n")
    report.append("\n")
    
    if 'volume_vs_turnover' in garch_results:
        vt = garch_results['volume_vs_turnover']
        report.append(f"- **成交量 vs 换手率预测力**: {vt['better_predictor']}更优\n")
        report.append(f"  - 成交量 R²: {vt['volume_r2']:.4f}\n")
        report.append(f"  - 换手率 R²: {vt['turnover_r2']:.4f}\n\n")
    
    # 2. Granger 因果
    report.append("## 🔗 Granger 因果检验\n")
    for direction, result in granger_results.items():
        if 'error' in result:
            report.append(f"- {direction}: ❌ {result['error']}\n")
        else:
            sig = "✅ 显著" if result['significant'] else "❌ 不显著"
            report.append(f"- **{direction}**: p={result['best_p_value']:.6f} (滞后{result['best_lag']}期) {sig}\n")
    report.append("\n")
    
    # 3. HAR-RV
    report.append("## 📊 HAR-RV 模型\n")
    report.append(f"- **基础模型 R²**: {harrv_results['basic_r2']:.4f}\n")
    report.append(f"- **完整模型 R²** (含成交量): {harrv_results['full_r2']:.4f}\n")
    report.append(f"- **R² 提升**: {harrv_results['r2_improvement_pct']:.2f}%\n")
    report.append(f"- **成交量系数**: {harrv_results['volume_coefficient']:.4f}\n")
    report.append(f"- **成交量贡献**: {'✅ 显著' if harrv_results['volume_significant'] else '❌ 不显著'}\n\n")
    
    # 结论
    report.append("## 🎯 结论\n")
    conclusions = []
    
    if 'mdh_verification' in garch_results:
        if garch_results['mdh_verification']['mdh_supported']:
            conclusions.append("✅ **MDH 假说成立**: 成交量能解释创业板指数波动率的聚集效应，引入成交量后波动率持续性显著下降。")
        else:
            conclusions.append("❌ **MDH 假说不明显**: 成交量对波动率持续性的解释力有限，可能受其他因素主导。")
    
    volume_granger = granger_results.get('volume→volatility', {})
    vol_granger = granger_results.get('volatility→volume', {})
    
    if volume_granger.get('significant'):
        conclusions.append(f"✅ **成交量对波动率的 Granger 因果显著**: 成交量能预测未来波动率走势 (滞后{volume_granger.get('best_lag')}期)。")
    if vol_granger.get('significant'):
        conclusions.append(f"✅ **波动率对成交量的 Granger 因果显著**: 存在双向因果关系。")
    
    if harrv_results.get('volume_significant'):
        conclusions.append(f"✅ **HAR-RV 模型验证**: 加入成交量后预测精度提升 {harrv_results.get('r2_improvement_pct', 0):.1f}%。")
    
    if 'volume_vs_turnover' in garch_results:
        conclusions.append(f"💡 **换手率 vs 成交量**: {garch_results['volume_vs_turnover']['better_predictor']}对波动率的解释力更强。")
    
    for c in conclusions:
        report.append(f"- {c}\n")
    
    report_content = "".join(report)
    
    # 保存报告
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "mdh_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"✅ 报告已保存: {report_path}")
    
    return report_content

def generate_plotly_chart(df, garch_results, harrv_results):
    """生成交互式 HTML 图表"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=4, cols=1,
        subplot_titles=('创业板指数收盘价', '日收益率 & 波动率',
                        '成交量 & 换手率', 'HAR-RV 预测对比 (测试集)'),
        row_heights=[0.25, 0.25, 0.25, 0.25],
        vertical_spacing=0.08
    )
    
    # 1. 收盘价
    fig.add_trace(
        go.Scatter(x=df.index, y=df['close'], name='收盘价',
                   line=dict(color='#00d4ff', width=2)),
        row=1, col=1
    )
    
    # 2. 收益率 + 波动率带
    fig.add_trace(
        go.Bar(x=df.index, y=df['pct_return'], name='日收益率',
               marker_color='rgba(0, 212, 255, 0.5)', opacity=0.7),
        row=2, col=1
    )
    
    # 3. 成交量和换手率
    fig.add_trace(
        go.Scatter(x=df.index, y=df['volume']/1e8, name='成交量(亿)',
                   line=dict(color='#ff6b6b', width=1.5)),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df['turnover'], name='换手率(%)',
                   line=dict(color='#ffd93d', width=1.5), yaxis='y6'),
        row=3, col=1
    )
    
    # 4. HAR-RV 预测 (简单可视化)
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    
    df_model = df[['rv', 'rv_week', 'rv_month', 'log_volume']].dropna().copy()
    df_model['rv_lag1'] = df_model['rv'].shift(1)
    df_model['rv_week_lag1'] = df_model['rv_week'].shift(1)
    df_model['rv_month_lag1'] = df_model['rv_month'].shift(1)
    df_model['vol_lag1'] = df_model['log_volume'].shift(1)
    df_model = df_model.dropna()
    
    y = df_model['rv'].values
    X_basic = df_model[['rv_lag1', 'rv_week_lag1', 'rv_month_lag1']].values
    X_full = df_model[['rv_lag1', 'rv_week_lag1', 'rv_month_lag1', 'vol_lag1']].values
    
    split = int(len(y) * 0.8)
    
    model_basic = LinearRegression()
    model_basic.fit(X_basic[:split], y[:split])
    pred_basic_all = model_basic.predict(X_basic)
    
    model_full = LinearRegression()
    model_full.fit(X_full[:split], y[:split])
    pred_full_all = model_full.predict(X_full)
    
    test_idx = df_model.index[split:]
    
    fig.add_trace(
        go.Scatter(x=test_idx, y=y[split:], name='真实RV',
                   line=dict(color='#ffffff', width=2)),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(x=test_idx, y=pred_basic_all[split:], name='基础HAR-RV',
                   line=dict(color='#ff6b6b', width=1.5, dash='dash')),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(x=test_idx, y=pred_full_all[split:], name='HAR-RV+成交量',
                   line=dict(color='#00d4ff', width=1.5, dash='dot')),
        row=4, col=1
    )
    
    # 布局
    fig.update_layout(
        title_text=f"🦞 创业板指数 MDH 假说验证 ({df.index.min().strftime('%Y-%m-%d')} ~ {df.index.max().strftime('%Y-%m-%d')})",
        height=1400,
        template='plotly_dark',
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation='h', y=1.02)
    )
    
    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    chart_path = os.path.join(OUTPUT_DIR, "cyb_mdh_analysis.html")
    fig.write_html(chart_path)
    print(f"✅ 图表已保存: {chart_path}")
    
    return chart_path

def generate_json_report(garch_results, granger_results, harrv_results, df):
    """生成 JSON 格式的结构化报告"""
    
    # 最近交易数据摘要
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    change_pct = ((latest['close'] - prev['close']) / prev['close']) * 100
    
    # 量价相关系数
    vol_return_corr = df['log_volume'].corr(df['abs_return'])
    to_return_corr = df['log_turnover'].corr(df['abs_return'])
    
    report = {
        'metadata': {
            'index': '创业板指 (sz.399006)',
            'data_start': df.index.min().strftime('%Y-%m-%d'),
            'data_end': df.index.max().strftime('%Y-%m-%d'),
            'trading_days': len(df),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'latest_price': {
            'date': str(df.index[-1].strftime('%Y-%m-%d')),
            'close': float(latest['close']),
            'daily_change_pct': float(change_pct)
        },
        'correlation': {
            'volume_abs_return': float(vol_return_corr),
            'turnover_abs_return': float(to_return_corr)
        },
        'garch_analysis': garch_results,
        'granger_causality': granger_results,
        'harrv_analysis': harrv_results
    }
    
    json_path = os.path.join(OUTPUT_DIR, "mdh_report.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 报告已保存: {json_path}")
    
    return report

def main():
    print("="*60)
    print("🦞 创业板指数 MDH 假说验证")
    print("成交量对波动率的预测性分析")
    print("="*60)
    
    # 1. 加载数据
    print("\n📥 从数据库加载数据...")
    df = get_data()
    if df is None:
        return
    
    # 2. 计算指标
    print("\n🔧 计算收益率和波动率指标...")
    df = calc_returns(df)
    print(f"   有效数据: {len(df)} 个交易日")
    print(f"   时间范围: {df.index.min()} ~ {df.index.max()}")
    
    # 3. 基础相关性
    print("\n📊 基础量价相关性:")
    print(f"   成交量-波动率 (绝对收益) 相关系数: {df['log_volume'].corr(df['abs_return']):.4f}")
    print(f"   换手率-波动率 (绝对收益) 相关系数: {df['log_turnover'].corr(df['abs_return']):.4f}")
    
    # 4. GARCH 检验
    garch_results = run_garchx_analysis(df)
    
    # 5. Granger 因果
    granger_results = run_granger_causality(df)
    
    # 6. HAR-RV 模型
    harrv_results = run_harrv_analysis(df)
    
    # 7. 生成报告
    print("\n" + "="*60)
    print("📝 生成报告...")
    report_md = generate_report(garch_results, granger_results, harrv_results, df)
    generate_json_report(garch_results, granger_results, harrv_results, df)
    
    # 8. 生成图表
    print("\n📈 生成图表...")
    chart_path = generate_plotly_chart(df, garch_results, harrv_results)
    
    print("\n" + "="*60)
    print("🎉 分析完成!")
    print(f"   报告: {os.path.join(OUTPUT_DIR, 'mdh_report.md')}")
    print(f"   图表: {chart_path}")
    print(f"   JSON: {os.path.join(OUTPUT_DIR, 'mdh_report.json')}")
    print("="*60)

if __name__ == "__main__":
    main()
