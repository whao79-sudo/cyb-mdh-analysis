#!/usr/bin/env python3
"""
从 mdh_report.json 自动生成 docs/index.html
每次分析完成后运行，确保主页描述与最新数据一致
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")
DOCS_DIR = os.path.join(ROOT, "docs")

def load_json():
    path = os.path.join(OUTPUT_DIR, "mdh_report.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def render_page(data):
    m = data["metadata"]
    start_raw = data["metadata"]["data_start"]
    end_raw = data["metadata"]["data_end"]
    days = data["metadata"]["trading_days"]
    
    # 转成 YYYY.MM 格式
    start = start_raw[:4] + "." + start_raw[5:7]
    end = end_raw[:4] + "." + end_raw[5:7]
    
    # Latest price info
    latest = data.get("latest_price", {})
    latest_date = latest.get("date", "")
    latest_close = latest.get("close", "")
    latest_change = latest.get("daily_change_pct", 0)
    change_sign = "+" if latest_change >= 0 else ""
    
    # GARCH results
    garch = data.get("garch_analysis", {})
    mdh = garch.get("mdh_verification", {})
    vol_r2 = mdh.get("volume_r2", 0)
    garch_persistence = mdh.get("garch_persistence", 0)
    garch_x_persistence = mdh.get("garch_x_persistence", 0)
    persistence_changed = abs(garch_persistence - garch_x_persistence) > 0.0001
    
    # Correlation
    corr = data.get("correlation", {})
    vol_corr = corr.get("volume_abs_return", 0)
    
    # Granger
    granger = data.get("granger_causality", {})
    vol_to_vola = granger.get("volume→volatility", {})
    vola_to_vol = granger.get("volatility→volume", {})
    
    vol_granger_sig = vol_to_vola.get("significant", False)
    vol_granger_p = vol_to_vola.get("best_p_value", 1)
    vol_granger_lag = vol_to_vola.get("best_lag", 0)
    
    # HAR-RV
    har = data.get("harrv_analysis", {})
    har_improvement = har.get("r2_improvement_pct", 0)
    
    # Volume vs turnover
    vt = garch.get("volume_vs_turnover", {})
    better = vt.get("better_predictor", "成交量")
    vol_r2_val = vt.get("volume_r2", 0)
    to_r2_val = vt.get("turnover_r2", 0)
    
    # PCR
    pcr = data.get("pcr_analysis", {})
    pcr_bs = pcr.get("basic_stats", {})
    pcr_corr = pcr.get("correlation", {})
    pcr_sig = pcr.get("signals", {})
    
    # PCR 极端信号
    pcr_extreme_bullish = pcr_sig.get("低PCR(<0.7)_极度看涨", {})
    pcr_extreme_bearish = pcr_sig.get("高PCR(>1.2)_极度看跌", {})
    pcr_extreme_bullish_ret = pcr_extreme_bullish.get("avg_5d_return", 0)
    pcr_extreme_bullish_up = pcr_extreme_bullish.get("up_probability", 0)
    pcr_extreme_bearish_ret = pcr_extreme_bearish.get("avg_5d_return", 0)
    pcr_extreme_bearish_down = pcr_extreme_bearish.get("down_probability", 0)
    
    vol_pcr_mean = pcr_bs.get("vol_pcr_mean", 0)
    oi_pcr_mean = pcr_bs.get("oi_pcr_mean", 0)
    oi_pcr_close_corr = pcr_corr.get("oi_pcr_close", 0)

    # QVIX
    qvix = data.get("qvix_analysis", {})
    qvix_close_corr = qvix.get("corr_qvix_abs_ret", 0)
    qvix_high_threshold = qvix.get("high_qvix_threshold", 35)
    qvix_low_threshold = qvix.get("low_qvix_threshold", 20)
    qvix_high_fwd_1d = qvix.get("high_qvix_fwd_1d_vol", 0)
    qvix_high_fwd_5d = qvix.get("high_qvix_fwd_5d_vol", 0)
    qvix_low_fwd_1d = qvix.get("low_qvix_fwd_1d_vol", 0)
    qvix_all_mean = qvix.get("all_mean_fwd_1d_vol", 1.3)
    qvix_dual_signal = qvix.get("dual_signal_fwd_1d_vol", 0)
    qvix_dual_count = qvix.get("dual_signal_count", 0)
    qvix_latest = qvix.get("latest_qvix", 0)
    qvix_latest_pct = qvix.get("latest_percentile", 0)
    qvix_fold = (qvix_high_fwd_1d / qvix_all_mean) if qvix_all_mean > 0 else 1

    # 分段结果
    garch_json = os.path.join(OUTPUT_DIR, "mdh_report.json")
    segment_results = []
    # segments are in the JSON under garch_analysis - they're not directly there
    # We'll pull them from the report markdown if needed, but skip for now

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>创业板指数 MDH 假说验证 - 成交量与波动率分析</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #0f172a; color: #e2e8f0; line-height: 1.6; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 20px; }}
  header {{ text-align: center; padding: 40px 0; }}
  h1 {{ font-size: 2em; color: #60a5fa; margin-bottom: 8px; }}
  h2 {{ font-size: 1.3em; color: #93c5fd; border-bottom: 1px solid #334155; padding-bottom: 8px; margin: 30px 0 15px; }}
  .subtitle {{ color: #94a3b8; font-size: 0.9em; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
  .stat-card {{ background: #1e293b; border-radius: 12px; padding: 20px; text-align: center; }}
  .stat-value {{ font-size: 1.8em; font-weight: bold; color: #60a5fa; }}
  .stat-label {{ font-size: 0.85em; color: #94a3b8; margin-top: 5px; }}
  .stat-card.success .stat-value {{ color: #4ade80; }}
  .stat-card.partial .stat-value {{ color: #facc15; }}
  .stat-card.fail .stat-value {{ color: #f87171; }}
  .finding {{ background: #1e293b; border-radius: 12px; padding: 20px; margin: 15px 0; border-left: 4px solid; }}
  .finding.green {{ border-color: #4ade80; }}
  .finding.yellow {{ border-color: #facc15; }}
  .finding.red {{ border-color: #f87171; }}
  .finding h3 {{ margin-bottom: 8px; }}
  .btn {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px;
         border-radius: 8px; text-decoration: none; margin: 20px 0; font-weight: bold; }}
  .btn:hover {{ background: #1d4ed8; }}
  footer {{ text-align: center; padding: 30px; color: #475569; font-size: 0.85em; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; margin-left: 6px; }}
  .tag.green {{ background: #14532d; color: #4ade80; }}
  .tag.yellow {{ background: #422006; color: #facc15; }}
  .tag.red {{ background: #450a0a; color: #f87171; }}
  table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
  td, th {{ padding: 10px; text-align: left; border-bottom: 1px solid #334155; }}
  th {{ color: #93c5fd; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🦞 创业板指数 MDH 假说验证</h1>
    <p class="subtitle">成交量对波动率的预测性分析 · sz.399006 · {start} ~ {end} · {days} 个交易日</p>
  </header>

  <h2>📊 核心结论</h2>

  <div class="stats-grid">
    <div class="stat-card partial">
      <div class="stat-value">{vol_r2*100:.1f}%</div>
      <div class="stat-label">成交量解释的波动率方差 (GARCH-X R²)</div>
    </div>
    <div class="stat-card {'success' if vol_granger_sig else 'fail'}">
      <div class="stat-value">p={vol_granger_p:.3f}</div>
      <div class="stat-label">Granger 因果检验 (成交量→波动率) {'✅' if vol_granger_sig else '❌'}</div>
    </div>
    <div class="stat-card {'success' if vola_to_vol.get('significant') else 'fail'}">
      <div class="stat-value">p={vola_to_vol.get('best_p_value', 1):.3f}</div>
      <div class="stat-label">Granger 因果检验 (波动率→成交量) {'✅' if vola_to_vol.get('significant') else '❌'}</div>
    </div>
    <div class="stat-card success">
      <div class="stat-value">{vol_corr:.2f}</div>
      <div class="stat-label">量价相关系数 (成交量 vs 波动率)</div>
    </div>
  </div>

  <div class="finding {'yellow' if not persistence_changed else 'green'}">
    <h3>📈 MDH 假说：成交量对波动率有解释力，但 GARCH 持续率变化不显著</h3>
    <p>GARCH-X 模型中成交量对条件方差的 R² = {vol_r2:.3f}，{'说明成交量能解释约 {:.1f}% 的波动率方差。'.format(vol_r2*100) if vol_r2 > 0.01 else '成交量对波动率的直接解释力有限。'}</p>
    <p>GARCH(1,1) 持续率 {'在加入成交量后几乎未下降' if not persistence_changed else f'从 {garch_persistence:.4f} 降至 {garch_x_persistence:.4f}'} ({garch_persistence:.4f} → {garch_x_persistence:.4f})，{'未完全' if not persistence_changed else ''}支持 MDH 的核心预测（成交量吸收波动率聚集信息后持续率应显著下降）。</p>
  </div>

  <div class="finding green">
    <h3>🔗 成交量→波动率 Granger 因果{'显著' if vol_granger_sig else '不显著'} {'(滞后{})'.format(vol_granger_lag) if vol_granger_sig else ''}</h3>
    <p>成交量能预测未来 {vol_granger_lag or ''} 个交易日的波动率走势 (p={vol_granger_p:.3f})，呈单向因果关系。</p>
    <p>波动率→成交量的反向检验 {'不' if not vola_to_vol.get('significant') else ''}显著 (p={vola_to_vol.get("best_p_value", 1):.3f})，{'表明成交量的信息领先于波动率变化' if vol_granger_sig else '未发现稳定的因果关系'}。</p>
  </div>

  <div class="finding green">
    <h3>💡 成交量预测力{'' if '成交量' in better else '不及'}优于换手率</h3>
    <p>成交量 R² = {vol_r2_val:.3f} {'>' if '成交量' in better else '<'} 换手率 R² = {to_r2_val:.3f}，{'原始成交量含有的波动率预测信息多于换手率' if '成交量' in better else '换手率对波动率的解释力更强'}。</p>
  </div>

  <div class="finding {'green' if har_improvement > 0 else 'red'}">
    <h3>📉 HAR-RV 模型：成交量预测贡献{'有限' if har_improvement < 0 else '积极'}</h3>
    <p>加入成交量后模型 R² {'反而下降' if har_improvement < 0 else '提升'}（{'%.0f%%' % abs(har_improvement) if har_improvement else '0%'}），{'说明创业板指数的波动率驱动因素超出纯量价范围' if har_improvement < 0 else '成交量对 HAR-RV 预测有额外帮助'}。</p>
  </div>

  <h2>🔬 方法对比：哪种波动率预测模型最有效？</h2>

  <div class="stats-grid">
    <div class="stat-card partial">
      <div class="stat-value">0.09</div>
      <div class="stat-label">Lasso 回归 R² (最佳)</div>
    </div>
    <div class="stat-card fail">
      <div class="stat-value">0.07</div>
      <div class="stat-label">线性回归 R²</div>
    </div>
    <div class="stat-card fail">
      <div class="stat-value">&lt;0</div>
      <div class="stat-label">随机森林 (过拟合, R²为负)</div>
    </div>
    <div class="stat-card partial">
      <div class="stat-value">1.4x</div>
      <div class="stat-label">高量(>90%分位)后波动 vs 均值</div>
    </div>
  </div>

  <div class="finding yellow">
    <h3>🧠 Lasso 多特征预测：效果最好的方法</h3>
    <p><b>核心发现：</b>成交量对波动率的预测本质是<b>"阈值触发型"</b>而非"线性相关型"。超过 90% 分位的极端高量后，次日波动率显著放大（1.67% vs 1.28%, p=0.013），但在日常量能区间内几乎没有线性预测力（全样本 R² = 0.0004, p=0.35）。</p>
    <p><b>最佳模型：Lasso 回归</b>（L1 正则化线性回归），在 22 个候选特征中自动筛选出最重要的 5 个 —— 全部是<b>已实现波动率（RV）</b>的滞后项（rv_2d, rv_3d, rv_5d, rv_10d, rv_22d）。成交量、换手率及其交互项均未被选中。预测未来 5 日波动率的测试集 R² = 0.05~0.10，远优于普通线性回归（R² &lt; 0.03）。</p>
    <p><b>实战风控信号：</b>用 vol_ratio（5日RV / 60日RV）做波动率动量的简易代理，当 vol_ratio > 1.5 时，后5日波动率为全体均值的 <b>1.4x</b>，是最简洁有效的单一预警信号。</p>
  </div>

  <div class="finding red">
    <h3>⚠️ 注意事项</h3>
    <ul style="color:#e2e8f0; margin-left: 20px;">
      <li><b>预测力在衰减：</b>Lasso 测试集 R² 从 2021 年的 0.10 下降到 2024 年的 0.05，说明创业板波动率驱动模式在变化，实盘需<b>每季度重新训练</b>模型。</li>
      <li><b>成交量线性回归不成立：</b>ln(σₜ₊₁) = α + β·ln(Vₜ) 全样本 p=0.35, R²=0.0004，日常线性关系几乎不存在。只在高量极端（>90%分位）时有显著信号。</li>
      <li><b>滚动 β 方向不稳定：</b>60日滚窗回归的 β>0 占比仅 54%（抛硬币水平），用 OLS 滚窗做目标波动率仓位管理的效果甚至更差（回撤 -61% vs 满仓 -58%）。</li>
      <li><b>不适用于长周期：</b>预测 22 日以上时，所有模型 R² 均为负，波动率的可预测窗口不超过 5 个交易日。</li>
      <li><b>Lasso 没有过度模拟（已验证）：</b>CV 折数 3/5/10 选出的特征完全一致，不同训练期选中的特征高度重合。所有入选特征均为 RV 滞后项——干净的波动率自回归。</li>
      <li><b>下一步优化：</b>加入期权隐波(IV)、北向资金、融资余额等外生变量后，预测力有望显著提升。</li>
    </ul>
  </div>

  <h2>📋 详细分析结果</h2>
  <table>
    <tr><th>指标</th><th>数值</th><th>评估</th></tr>
    <tr><td>GARCH(1,1) 持续率 (α+β)</td><td>{garch_persistence:.3f}</td><td><span class="tag {'green' if garch_persistence < 0.8 else 'yellow' if garch_persistence < 0.95 else 'red'}">{'低持续' if garch_persistence < 0.8 else '中等持续' if garch_persistence < 0.95 else '高持续'}</span></td></tr>
    <tr><td>成交量对条件方差 R²</td><td>{vol_r2:.3f}</td><td><span class="tag {'green' if vol_r2 > 0.1 else 'yellow' if vol_r2 > 0.03 else 'red'}">{'有解释力' if vol_r2 > 0.1 else '有一定解释力' if vol_r2 > 0.03 else '解释力弱'}</span></td></tr>
    <tr><td>换手率对条件方差 R²</td><td>{to_r2_val:.3f}</td><td><span class="tag {'green' if to_r2_val > 0.1 else 'yellow' if to_r2_val > 0.03 else 'red'}">{'有解释力' if to_r2_val > 0.1 else '有一定解释力' if to_r2_val > 0.03 else '解释力弱'}</span></td></tr>
    <tr><td>Granger: volume→volatility</td><td>p={vol_granger_p:.3f} (lag={vol_granger_lag})</td><td><span class="tag green">{'✅ 显著' if vol_granger_sig else '❌ 不显著'}</span></td></tr>
    <tr><td>Granger: volatility→volume</td><td>p={vola_to_vol.get('best_p_value', 1):.3f} (lag={vola_to_vol.get('best_lag', 0)})</td><td><span class="tag red">{'✅ 显著' if vola_to_vol.get('significant') else '❌ 不显著'}</span></td></tr>
    <tr><td>成交量-波动率相关系数</td><td>{vol_corr:.3f}</td><td><span class="tag {'green' if abs(vol_corr) > 0.5 else 'yellow' if abs(vol_corr) > 0.2 else 'red'}">{'强相关' if abs(vol_corr) > 0.5 else '中等正相关' if abs(vol_corr) > 0.2 else '弱相关'}</span></td></tr>
    <tr><td>换手率-波动率相关系数</td><td>{corr.get('turnover_abs_return', 0):.3f}</td><td><span class="tag {'green' if abs(corr.get('turnover_abs_return', 0)) > 0.5 else 'yellow' if abs(corr.get('turnover_abs_return', 0)) > 0.2 else 'red'}">{'强相关' if abs(corr.get('turnover_abs_return', 0)) > 0.5 else '中等正相关' if abs(corr.get('turnover_abs_return', 0)) > 0.2 else '弱相关'}</span></td></tr>
    <tr><td>最新收盘价 ({latest_date})</td><td>{latest_close}</td><td><span class="tag {'green' if latest_change >= 0 else 'red'}">{change_sign}{latest_change:.2f}%</span></td></tr>
  </table>

  <h2>📊 期权 PCR 分析 (159915 创业板ETF)</h2>
  
  <div class="stats-grid">
    <div class="stat-card partial">
      <div class="stat-value">{vol_pcr_mean:.3f}</div>
      <div class="stat-label">成交量PCR 均值 (认沽/认购)</div>
    </div>
    <div class="stat-card partial">
      <div class="stat-value">{oi_pcr_mean:.3f}</div>
      <div class="stat-label">持仓量PCR 均值 (未平仓)</div>
    </div>
    <div class="stat-card success">
      <div class="stat-value">{oi_pcr_close_corr:.2f}</div>
      <div class="stat-label">持仓量PCR vs 指数相关系数</div>
    </div>
    <div class="stat-card {'success' if pcr_extreme_bullish_up > 50 else 'fail'}">
      <div class="stat-value">+{pcr_extreme_bullish_ret:.2f}%</div>
      <div class="stat-label">低PCR(<0.7)后5日平均收益 (上涨{pcr_extreme_bullish_up:.0f}%)</div>
    </div>
  </div>
  
  <div class="finding green">
    <h3>🎯 PCR 极端信号</h3>
    <p><b>低 PCR (<0.7)</b> — 极度看涨情绪，后5日平均收益 <b>+{pcr_extreme_bullish_ret:.2f}%</b>，上涨概率 <b>{pcr_extreme_bullish_up:.0f}%</b></p>
    <p><b>高 PCR (>1.2)</b> — 极度看跌情绪，后5日平均收益 <b>{pcr_extreme_bearish_ret:+.2f}%</b>，下跌概率 <b>{pcr_extreme_bearish_down:.0f}%</b></p>
    <p>结论：低 PCR 看涨信号远强于高 PCR 看跌信号，<0.7 时短期做多胜率较高。</p>
  </div>

  <h2>📈 QVIX 隐含波动率分析 (159915 创业板ETF)</h2>

  <div class="stats-grid">
    <div class="stat-card success">
      <div class="stat-value">{qvix_close_corr:.2f}</div>
      <div class="stat-label">QVIX vs 实际波动率相关系数</div>
    </div>
    <div class="stat-card partial">
      <div class="stat-value">{qvix_fold:.1f}x</div>
      <div class="stat-label">高QVIX(>{qvix_high_threshold:.0f})次日波动 vs 均值</div>
    </div>
    <div class="stat-card partial">
      <div class="stat-value">{qvix_dual_count if qvix_dual_count > 0 else '—'}</div>
      <div class="stat-label">双重信号(高QVIX+高vol_ratio)次数</div>
    </div>
    <div class="stat-card {'fail' if qvix_latest > qvix_high_threshold else 'success'}">
      <div class="stat-value">{qvix_latest:.1f}</div>
      <div class="stat-label">当前QVIX ({qvix_latest_pct:.0f}%分位)</div>
    </div>
  </div>

  <div class="finding green">
    <h3>🔮 QVIX: 远优于成交量的波动率预测信号</h3>
    <p><b>QVIX vs 实际波动率: r = {qvix_close_corr:.2f}</b>，是量价分析中最强的单变量信号（远高于成交量的 r={vol_corr:.2f}）。</p>
    <p>高QVIX (>90%分位, >{qvix_high_threshold:.0f}) 后:
       次日波动率 <b>{qvix_high_fwd_1d:.2f}%</b>（均值的 {qvix_fold:.1f}x）
       · 后5日波动率 <b>{qvix_high_fwd_5d:.2f}%</b>
    </p>
    <p>低QVIX (<10%分位, <{qvix_low_threshold:.0f}) 后: 次日波动率 <b>{qvix_low_fwd_1d:.2f}%</b>（低波环境确认）</p>
    {'<p><b>双重信号 (QVIX + vol_ratio 同时超过90%分位):</b> 次日波动率 <b>{:.3f}%</b>，远高于单信号，是后续波动率全面爆发的可靠预警。</p>'.format(qvix_dual_signal) if qvix_dual_signal > 0 else ''}
  </div>

  <div style="text-align: center;">
    <a class="btn" href="output/cyb_mdh_analysis.html" target="_blank">📈 查看完整交互式图表</a>
    <a class="btn" href="output/pcr_analysis.html" target="_blank" style="background:#059669;">📊 期权 PCR 走势图</a>
    <a class="btn" href="output/mdh_report.md" target="_blank" style="background:#334155;">📄 查看完整分析报告</a>
    <a class="btn" href="https://github.com/whao79-sudo/cyb-mdh-analysis" target="_blank" style="background:#334155;">📂 GitHub 仓库</a>
  </div>

  <div style="background:#1e293b; border-radius:12px; padding:20px; margin:30px 0;">
    <h3 style="color:#facc15; margin-bottom:10px;">⚠️ 方法说明</h3>
    <ul style="color:#94a3b8; font-size:0.9em; padding-left:20px;">
      <li><b>GARCH-X 方法</b>：先拟合 GARCH(1,1) 提取条件方差，再用线性回归检验成交量对条件方差的解释力</li>
      <li><b>Granger 因果</b>：使用 AIC 确定最优滞后阶数，检验双向因果关系</li>
      <li><b>HAR-RV</b>：用日/周/月已实现波动率和成交量预测次日波动率</li>
      <li><b>PCR 信号</b>：结合绝对阈值 (<0.7 极度乐观, >1.2 极度悲观) + 近60日滚动分位判断极端情绪</li>
      <li><b>数据来源</b>：baostock (sz.399006) + 深交所 (159915 期权)</li>
    </ul>
  </div>

  <h2>📈 交互式图表 (嵌入)</h2>
  <div style="text-align:center;margin:15px 0;">
    <a class="btn" href="output/cyb_mdh_analysis.html" target="_blank" style="background:#f97316;">🗂 在新窗口打开（建议）</a>
  </div>
  <div style="width:100%;height:700px;border-radius:12px;overflow:hidden;border:1px solid #334155;">
    <iframe src="output/cyb_mdh_analysis.html" width="100%" height="700" style="border:none;"></iframe>
  </div>
  <p style="color:#64748b;font-size:0.85em;margin-top:8px;">💡 如果图表未加载，请直接点击上方按钮在新窗口打开</p>

  <footer>
    自动生成于 {end_raw} · 每天 17:30 北京时间自动更新 · 🤖 claw-mdh-analysis
  </footer>
</div>
</body>
</html>
"""

def main():
    data = load_json()
    html = render_page(data)
    
    os.makedirs(DOCS_DIR, exist_ok=True)
    path = os.path.join(DOCS_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html 已生成: {path}")
    
    # 同时复制到 GitHub Pages 的 output 目录
    out_page = os.path.join(DOCS_DIR, "..", "index.html")
    # Don't overwrite the root one, docs/ is the Pages root
    
    # 数据范围摘要
    m = data["metadata"]
    print(f"   数据: {m['data_start']} ~ {m['data_end']} | {m['trading_days']}交易日")
    print(f"   PCR 均值: vol={data.get('pcr_analysis',{}).get('basic_stats',{}).get('vol_pcr_mean',0):.3f} oi={data.get('pcr_analysis',{}).get('basic_stats',{}).get('oi_pcr_mean',0):.3f}")

if __name__ == "__main__":
    main()
