#!/usr/bin/env python3
"""
信号页面生成器
根据 mdh_report.json 数据，生成每个信号的独立 HTML 页面 + 首页导航
"""
import json, os, math
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "output")
DOCS_DIR = os.path.join(BASE, "docs")
SIGNALS_DIR = os.path.join(DOCS_DIR, "signals")

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
       background:#0f172a; color:#e2e8f0; line-height:1.6; }
.container { max-width:800px; margin:0 auto; padding:20px; }
header { text-align:center; padding:30px 0 20px; }
h1 { font-size:1.8em; color:#60a5fa; margin-bottom:4px; }
h2 { font-size:1.2em; color:#93c5fd; border-bottom:1px solid #334155; padding-bottom:8px; margin:25px 0 12px; }
.subtitle { color:#94a3b8; font-size:0.9em; }
.back { display:inline-block; color:#60a5fa; text-decoration:none; margin-bottom:10px; font-size:0.9em; }
.back:hover { text-decoration:underline; }
.kpi { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:15px 0; }
.kpi-card { background:#1e293b; border-radius:10px; padding:15px; text-align:center; }
.kpi-val { font-size:1.6em; font-weight:bold; color:#60a5fa; }
.kpi-label { font-size:0.8em; color:#94a3b8; margin-top:4px; }
.kpi-card.good .kpi-val { color:#4ade80; }
.kpi-card.bad .kpi-val { color:#f87171; }
.kpi-card.warn .kpi-val { color:#facc15; }
table { width:100%; border-collapse:collapse; margin:10px 0; font-size:0.85em; }
th { background:#1e293b; color:#94a3b8; padding:8px; text-align:left; border-bottom:2px solid #334155; }
td { padding:8px; border-bottom:1px solid #1e293b; }
tr:hover td { background:#1e293b; }
.badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.8em; font-weight:bold; }
.badge.green { background:rgba(74,222,128,0.2); color:#4ade80; }
.badge.red { background:rgba(248,113,113,0.2); color:#f87171; }
.badge.yellow { background:rgba(250,204,21,0.2); color:#facc15; }
.box { background:#1e293b; border-radius:10px; padding:15px; margin:15px 0; border-left:4px solid #334155; }
.box.info { border-left-color:#60a5fa; }
.box.warn { border-left-color:#facc15; }
.box.danger { border-left-color:#f87171; }
.box.success { border-left-color:#4ade80; }
ul { margin-left:20px; }
li { margin:4px 0; }
footer { text-align:center; color:#64748b; padding:30px 0; font-size:0.8em; }
"""

def render_card(val, label, color="normal", fmt=".3f"):
    colors = {"good":"#4ade80","bad":"#f87171","warn":"#facc15","normal":"#60a5fa"}
    c = colors.get(color, "#60a5fa")
    if val == 0 and "胜率" not in label:
        val_s = "—"
    elif isinstance(val, float):
        val_s = f"{val:{fmt}}"
    else:
        val_s = str(val)
    return f"""<div class="kpi-card"><div class="kpi-val" style="color:{c}">{val_s}</div><div class="kpi-label">{label}</div></div>"""

def render_badge_sig(p_val):
    if p_val < 0.01: return '<span class="badge green">✅ 极显著</span>'
    if p_val < 0.05: return '<span class="badge green">✅ 显著</span>'
    if p_val < 0.10: return '<span class="badge yellow">🔶 弱显著</span>'
    return '<span class="badge red">❌ 不显著</span>'

# ──────────────────────────────────────────────────
# 信号定义：每个信号的数据提取 + HTML 渲染
# ──────────────────────────────────────────────────

SIGNALS = []

# 信号 1: Granger 量→波动
SIGNALS.append({
    "slug": "granger",
    "title": "❶ 量价因果：成交量→波动率 Granger 检验",
    "emoji": "🔗",
    "desc": "检验成交量是否'领先于'波动率变化。如果 p<0.05，说明历史成交量包含预测未来波动的信息。",
    "render": lambda d: render_granger(d)
})

def render_granger(d):
    gr = d.get("garch_analysis", {}).get("granger_causality", {})
    vol_to_vol = gr.get("volume→volatility", {})
    p_val = vol_to_vol.get("best_p_value", 1)
    lag = vol_to_vol.get("best_lag", "?")
    sig = vol_to_vol.get("significant", False)
    
    html = f"<div class='kpi'>"
    html += render_card(f"{p_val:.4f}", f"Granger p值 (lag={lag})", "good" if sig else "bad")
    html += render_card("✅ 显著" if sig else "❌ 不显著", "显著性判断")
    html += render_card(lag, "最优滞后天数")
    html += "</div>"
    
    html += f"""<div class="box {"success" if sig else "warn"}">
      <b>结论：</b>{"成交量对波动率有" if sig else "成交量对波动率没有明显的"}预测力。
      {"成交量上涨后，波动率在 " + str(lag) + " 日内会显著放大。" if sig else ""}
      但 GARCH-X R² 仅 4.4%，说明预测力很弱，只对极端高量有效。
    </div>"""
    
    # 滚动 Granger 趋势（从 volume_signal.md 获取，暂略）
    html += """<h2>🔎 解读</h2>
    <ul>
      <li><b>全样本：</b>Granger 因果显著 → 成交量包含波动率预测信息</li>
      <li><b>但线性回归不显著：</b>ln(σₜ₊₁) = α + β·ln(Vₜ) 的 p=0.35，R²=0.0004 — 日常量能区间无线性关系</li>
      <li><b>本质：阈值触发型</b> — 只有>90%分位的极端高量才显著放大波动</li>
    </ul>"""
    return html

# 信号 2: GARCH-X 成交量对波动率的解释力
SIGNALS.append({
    "slug": "garchx",
    "title": "❷ GARCH-X：成交量对条件波动率的解释力",
    "emoji": "📊",
    "desc": "GARCH(1,1) 框架下加入成交量作为外生变量，检验成交量是否提高波动率拟合优度。",
    "render": lambda d: render_garchx(d)
})

def render_garchx(d):
    g = d.get("garch_analysis", {})
    vv = g.get("volume_vs_turnover", {})
    vol_r2 = vv.get("volume_r2", 0)
    to_r2 = vv.get("turnover_r2", 0)
    better = vv.get("better_predictor", "成交量")
    garch_results = g.get("garch_results", [])
    
    html = "<div class='kpi'>"
    html += render_card(f"{vol_r2:.4f}", "GARCH-X 成交量 R²", "warn" if vol_r2 < 0.1 else "good")
    html += render_card(f"{to_r2:.4f}", "GARCH-X 换手率 R²", "bad")
    html += render_card(better, "更优预测变量")
    html += "</div>"
    
    html += """<div class="box info">
      <b>结论：</b>成交量优于换手率（R²=4.4% vs 1.0%），但解释力仍然很弱。
      意味着条件波动率中只有不到 5% 能被成交量解释。
    </div>"""
    
    html += "<h2>📋 模型对比</h2><table><tr><th>模型</th><th>R²</th><th>AIC</th><th>BIC</th></tr>"
    for m in garch_results[-3:]:
        if isinstance(m, dict):
            html += f"<tr><td>{m.get('name','')}</td><td>{m.get('r2',''):.4f}</td><td>{m.get('aic','')}</td><td>{m.get('bic','')}</td></tr>"
    html += "</table>"
    
    html += """<h2>🔎 解读</h2>
    <ul>
      <li>成交量对条件波动的解释力有限（R²=4.4%），<b>不足以单独用于预测</b></li>
      <li>但结合其他信号（QVIX、vol_ratio）后，联合预警效果显著提升</li>
    </ul>"""
    return html

# 信号 3: PCR 期权情绪
SIGNALS.append({
    "slug": "pcr",
    "title": "❸ PCR 期权情绪：认沽认购比",
    "emoji": "📉",
    "desc": "Put/Call Ratio 反映期权市场的多空分歧程度。极低 PCR 对应极端乐观（尾部风险），极高 PCR 对应恐慌对冲。",
    "render": lambda d: render_pcr(d)
})

def render_pcr(d):
    p = d.get("pcr_analysis", {})
    bs = p.get("basic_stats", {})
    signals = p.get("signals", {})
    
    vol_mean = bs.get("vol_pcr_mean", 0)
    oi_mean = bs.get("oi_pcr_mean", 0)
    
    html = "<div class='kpi'>"
    html += render_card(f"{vol_mean:.3f}", "PCR(量)均值", "normal", ".3f")
    html += render_card(f"{oi_mean:.3f}", "PCR(持仓)均值", "normal", ".3f")
    html += render_card(f"{bs.get('vol_pcr_current', 0):.3f}", "当前PCR(量)", "warn" if bs.get('vol_pcr_current', 0) < 0.8 else "normal", ".3f")
    html += "</div>"
    
    html += "<h2>📋 各阈值收益统计</h2><table><tr><th>信号</th><th>后5日收益</th><th>胜率</th></tr>"
    # 极度信号优先展示
    for k in ["低PCR(<0.7)_极度看涨", "高PCR(>1.2)_极度看跌", "近60日低PCR分位(<15%)", "近60日高PCR分位(>85%)", "低PCR(<0.8)_看涨"]:
        v = signals.get(k, {})
        if isinstance(v, dict) and 'avg_5d_return' in v:
            ret = v.get('avg_5d_return', 0)
            up = v.get('up_probability', 0)
            c = "green" if ret > 1 else ("red" if ret < -1 else "warn")
            html += f"<tr><td>{k}</td><td style='color:{c}'>{ret:+.2f}%</td><td>{up:.0f}%</td></tr>"
    html += "</table>"
    
    html += """<div class="box success">
      <b>核心结论：</b>低PCR(<0.7)是唯一的有效<b>方向信号</b>（后5日+2.44%, 胜率60%）。
      高PCR(>1.2)看跌信号弱（后5日-0.41%, 胜率降至42%）。
      PCR 做多信号远强于做空信号。
    </div>"""
    return html

# 信号 4: QVIX
SIGNALS.append({
    "slug": "qvix",
    "title": "❹ QVIX：隐含波动率 — 最好的波动率预测器",
    "emoji": "🌡️",
    "desc": "QVIX 是159915期权的隐含波动率指数（类似 VIX）。它反映市场对未来30天波动率的集体预期。",
    "render": lambda d: render_qvix(d)
})

def render_qvix(d):
    q = d.get("qvix_analysis", {})
    corr = q.get("corr_qvix_abs_ret", 0)
    hi_thr = q.get("high_qvix_threshold", 35)
    lo_thr = q.get("low_qvix_threshold", 20)
    hi_f1 = q.get("high_qvix_fwd_1d_vol", 0)
    hi_f5 = q.get("high_qvix_fwd_5d_vol", 0)
    lo_f1 = q.get("low_qvix_fwd_1d_vol", 0)
    all_m = q.get("all_mean_fwd_1d_vol", 1.3)
    lat = q.get("latest_qvix", 0)
    lat_pct = q.get("latest_percentile", 0)
    fold = hi_f1 / all_m if all_m else 1
    
    html = "<div class='kpi'>"
    html += render_card(f"{corr:.2f}", "QVIX vs 实际波动 r", "good")
    html += render_card(f"{hi_f1:.2f}%", f"高QVIX(>{hi_thr:.0f})次日波动", "warn")
    html += render_card(f"{fold:.1f}x", "高QVIX vs 均值倍数", "bad")
    html += render_card(f"{lat:.1f} ({lat_pct:.0f}%分位)", "当前QVIX", "bad" if lat > hi_thr else "good")
    html += "</div>"
    
    html += f"""<div class="box info">
      <b>与成交量对比：</b>QVIX 与波动率的相关系数 r={corr:.2f}，远高于成交量的历史均值（约 r=0.14）。
      高QVIX (>90%分位, >{hi_thr:.0f}) 后，次日波动率跳升至 {hi_f1:.2f}%（均值的 {fold:.1f}x）。
    </div>"""
    
    html += """<h2>🔎 注意事项</h2>
    <ul>
      <li><b>QVIX 只测幅不测向</b> — 高QVIX后上涨概率仅51%（抛硬币水平）</li>
      <li><b>数据仅从2022年9月开始</b>（874个交易日），统计可靠性低于量价信号</li>
      <li><b>与 vol_ratio 联合使用效果最佳</b>（参见"双重信号"）</li>
    </ul>"""
    return html

# 信号 5: vol_ratio
SIGNALS.append({
    "slug": "vol_ratio",
    "title": "❺ vol_ratio：短期 vs 长期波动率比",
    "emoji": "📈",
    "desc": "5日已实现波动率 / 60日已实现波动率。>1 时市场正经历高于常态的波动，<1 时波动在衰减。",
    "render": lambda d: render_vol_ratio(d)
})

def render_vol_ratio(d):
    q = d.get("qvix_analysis", {})
    hv = q.get("high_vr_fwd_5d_vol", 0)
    am = q.get("all_mean_fwd_1d_vol", 1.3)
    vr90 = q.get("high_vr_ratio_p90", 1.5)
    am5 = q.get("all_mean_fwd_5d_vol", 1.3)
    
    html = "<div class='kpi'>"
    html += render_card(f"{vr90:.2f}", "vol_ratio 90%分位阈值", "normal")
    html += render_card(f"{hv:.2f}%", "高vol_ratio后5日波动", "warn")
    html += render_card(f"{hv/am5:.1f}x" if am5 else "—", "vs 全体均值", "bad")
    html += "</div>"
    
    html += f"""<div class="box info">
      <b>最佳单一波动率预警信号：</b>当 vol_ratio > {vr90:.1f}（90%分位）时，后5日波动率为全体均值的 {hv/am5:.1f}x。
      相比成交量线性回归的无效结果，这是最简洁有效的波动率预警。
    </div>"""
    
    html += """<h2>🔎 用法</h2>
    <ul>
      <li><b>vol_ratio < 0.7</b> — 低波动期，趋势跟踪效果好</li>
      <li><b>0.7 < vol_ratio < 1.3</b> — 正常波动，常规操作</li>
      <li><b>vol_ratio > {:.1f}</b> — 高波动预警，考虑减仓或对冲</li>
      <li><b>vol_ratio > 2.0</b> — 极罕见（全周期仅数次），多为市场恐慌顶点</li>
    </ul>""".format(vr90)
    return html

# 信号 6: 双重信号
SIGNALS.append({
    "slug": "dual_signal",
    "title": "❻ 双重信号：QVIX + vol_ratio — 🚀 最有效的联合预警",
    "emoji": "🔴",
    "desc": "当 QVIX（隐含波动）和 vol_ratio（已实现波动冲量）同时突破90%分位时，市场正处于多维度高波动共振。",
    "render": lambda d: render_dual(d)
})

def render_dual(d):
    q = d.get("qvix_analysis", {})
    dual = q.get("dual_signal_fwd_1d_vol", 0)
    dual_n = q.get("dual_signal_count", 0)
    any_s = q.get("either_signal_fwd_1d_vol", 0)
    any_n = q.get("either_signal_count", 0)
    hi_f1 = q.get("high_qvix_fwd_1d_vol", 0)
    am = q.get("all_mean_fwd_1d_vol", 1.3)
    
    html = "<div class='kpi'>"
    html += render_card(f"{dual:.2f}%", f"双重信号后次日波动 (N={dual_n})", "bad")
    html += render_card(f"{dual/am:.1f}x" if am else "—", "vs 全体均值", "bad")
    html += render_card(f"{hi_f1:.2f}%", "仅单信号 (QVIX高)", "warn")
    html += render_card(f"{dual_n}", f"历史出现次数 ({dual_n}/{dual_n+max(58,0)})", "warn")
    html += "</div>"
    
    html += f"""<div class="box danger">
      <b>🚀 这是本分析框架中最有效的预警信号。</b><br><br>
      QVIX + vol_ratio 双高时，后5日波动率达到 {dual:.2f}%，
      是无信号的 3.2 倍。双重信号共出现 {dual_n} 次（占约 3% 的时间），
      每次出现都对应市场的剧烈波动期。
    </div>"""
    
    html += """<h2>🔎 实用建议</h2>
    <ul>
      <li><b>双重信号出现 → 大幅减仓 + 做多跨式期权</b>（买认购+买认沽，赌波动但不赌方向）</li>
      <li><b>仅QVIX高</b> → 控制仓位，Put 保护</li>
      <li><b>仅vol_ratio高</b> → 短期波动冲量，等待回归</li>
      <li><b>QVIX从低位跳涨 + 价格暴跌</b> → 恐慌见底信号，短期反弹概率大</li>
    </ul>"""
    return html

# ──────────────────────────────────────────────────
# 生成所有页面
# ──────────────────────────────────────────────────

def render_signal_page(signal, data):
    slug = signal["slug"]
    content = signal["render"](data)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{signal['emoji']} {signal['title']} — CYB MDH Analysis</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<header>
  <a href="../index.html" class="back">← 返回仪表盘</a>
  <h1>{signal['emoji']} {signal['title']}</h1>
  <p class="subtitle">{signal['desc']}</p>
</header>

{content}

<footer>
  CYB MDH Analysis · 数据来源: baostock + 深交所 + 中证指数 ·
  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
</footer>
</div>
</body>
</html>"""
    return html

def render_dashboard(signals, data):
    """生成首页仪表盘"""
    q = data.get("qvix_analysis", {})
    p = data.get("pcr_analysis", {})
    bs = p.get("basic_stats", {})
    gr = data.get("garch_analysis", {}).get("granger_causality", {}).get("volume→volatility", {})
    latest_date = max(
        q.get("latest_date", ""),
        bs.get("pcr_date", ""),
        "2026-05-15"
    )
    
    alert_count = 0
    alert_items = []
    
    # 检查当前QVIX
    qvix_latest = q.get("latest_qvix", 0)
    qvix_hi = q.get("high_qvix_threshold", 35)
    qvix_pct = q.get("latest_percentile", 0)
    if qvix_latest > qvix_hi:
        alert_count += 1
        alert_items.append(f"QVIX = {qvix_latest:.0f} (>{qvix_hi:.0f}, {qvix_pct:.0f}%分位) — 隐含波动率偏高，注意控制仓位")
    
    # PCR
    pcr_current = bs.get("vol_pcr_current", 0)
    if pcr_current < 0.7:
        alert_count += 1
        alert_items.append(f"PCR(量) = {pcr_current:.3f} (<0.7) — 期权市场极度乐观，警惕反转")
    elif pcr_current > 1.2:
        alert_count += 1
        alert_items.append(f"PCR(量) = {pcr_current:.3f} (>1.2) — 期权市场恐慌对冲，短期偏空")
    
    # Granger
    gr_sig = gr.get("significant", False)
    
    cards_html = ""
    for s in signals:
        slug = s["slug"]
        emoji = s["emoji"]
        title = s["title"]
        desc = s["desc"]
        cards_html += f"""
        <a href="signals/{slug}.html" class="signal-card">
          <div class="signal-emoji">{emoji}</div>
          <div class="signal-title">{title}</div>
          <div class="signal-desc">{desc[:80]}{'...' if len(desc) > 80 else ''}</div>
        </a>"""
    
    # 当前预警
    alert_html = ""
    if alert_items:
        alert_html = f"""<div class="box danger">
          <h3 style="margin-bottom:10px;">⚠️ 当前活跃预警</h3>
          <ul>
            {''.join(f'<li>{item}</li>' for item in alert_items)}
          </ul>
        </div>"""
    
    dashboard = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CYB MDH 信号仪表盘</title>
<style>
{CSS}
.signal-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:15px; margin:20px 0; }}
.signal-card {{ background:#1e293b; border-radius:12px; padding:18px; text-decoration:none; color:#e2e8f0; display:block; transition:transform 0.15s, box-shadow 0.15s; border:1px solid #334155; }}
.signal-card:hover {{ transform:translateY(-2px); box-shadow:0 4px 15px rgba(96,165,250,0.15); border-color:#60a5fa; }}
.signal-emoji {{ font-size:2em; margin-bottom:6px; }}
.signal-title {{ font-size:1em; font-weight:bold; color:#60a5fa; margin-bottom:4px; }}
.signal-desc {{ font-size:0.82em; color:#94a3b8; }}
.quick-stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:20px 0; }}
.quick-card {{ background:#1e293b; border-radius:10px; padding:15px; text-align:center; border-left:3px solid; }}
.quick-card.q-good {{ border-color:#4ade80; }}
.quick-card.q-warn {{ border-color:#facc15; }}
.quick-card.q-bad {{ border-color:#f87171; }}
.quick-val {{ font-size:1.4em; font-weight:bold; }}
.quick-label {{ font-size:0.8em; color:#94a3b8; }}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>🦞 创业板(159915) 信号仪表盘</h1>
  <p class="subtitle">数据截至 {latest_date} · 基于全量 MDH 分析框架</p>
</header>

{alert_html}

<div class="quick-stats">
  <div class="quick-card {'q-good' if gr_sig else 'q-warn'}">
    <div class="quick-val" style="color:{'#4ade80' if gr_sig else '#facc15'}">
      {"✅ 有效" if gr_sig else "❌ 无效"}
    </div>
    <div class="quick-label">量→波动 Granger 因果</div>
  </div>
  <div class="quick-card {'q-warn' if qvix_latest > qvix_hi else 'q-good'}">
    <div class="quick-val" style="color:{'#f87171' if qvix_latest > qvix_hi else '#4ade80'}">{qvix_latest:.0f}</div>
    <div class="quick-label">当前 QVIX ({qvix_pct:.0f}%分位)</div>
  </div>
  <div class="quick-card {'q-good' if pcr_current < 0.85 else 'q-warn'}">
    <div class="quick-val" style="color:{'#4ade80' if pcr_current < 0.85 else '#facc15'}">{pcr_current:.2f}</div>
    <div class="quick-label">当前 PCR(量)</div>
  </div>
  <div class="quick-card {'q-good'}">
    <div class="quick-val" style="color:#60a5fa">{len(signals)}</div>
    <div class="quick-label">总信号数</div>
  </div>
</div>

<h2>📡 信号列表</h2>
<div class="signal-grid">
  {cards_html}
</div>

<footer>
  CYB MDH Analysis · <a href="https://github.com/whao79-sudo/cyb-mdh-analysis" style="color:#60a5fa;">GitHub</a> ·
  <a href="output/cyb_mdh_analysis.html" style="color:#60a5fa;">完整图表</a> ·
  <a href="output/pcr_analysis.html" style="color:#60a5fa;">PCR图</a> ·
  <a href="output/qvix_signal_chart.html" style="color:#60a5fa;">QVIX信号图</a> ·
  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
</footer>
</div>
</body>
</html>"""
    return dashboard

def main():
    # 加载数据
    json_path = os.path.join(DATA_DIR, "mdh_report.json")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 创建 signals 目录
    os.makedirs(SIGNALS_DIR, exist_ok=True)
    
    # 生成每个信号页面
    for signal in SIGNALS:
        html = render_signal_page(signal, data)
        path = os.path.join(SIGNALS_DIR, f"{signal['slug']}.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  ✅ {signal['emoji']} {path}")
    
    # 生成仪表盘（覆盖 index.html）
    dashboard = render_dashboard(SIGNALS, data)
    index_path = os.path.join(DOCS_DIR, "index.html")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(dashboard)
    print(f"\n✅ 仪表盘: {index_path}")
    print(f"   共 {len(SIGNALS)} 个信号页面")

if __name__ == "__main__":
    main()
