#!/usr/bin/env python3
"""
信号页面生成器 v2 — 所有结论基于真实回测数据
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
h3 { color:#e2e8f0; margin:15px 0 8px; }
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

def card(val, label, color="normal", fmt=".3f"):
    colors = {"good":"#4ade80","bad":"#f87171","warn":"#facc15","normal":"#60a5fa"}
    c = colors.get(color, "#60a5fa")
    val_s = str(val) if not isinstance(val, float) else f"{val:{fmt}}"
    return f'<div class="kpi-card"><div class="kpi-val" style="color:{c}">{val_s}</div><div class="kpi-label">{label}</div></div>'

def badge_sig(p):
    if p < 0.01: return '<span class="badge green">&#9989; 极显著</span>'
    if p < 0.05: return '<span class="badge green">&#9989; 显著</span>'
    if p < 0.10: return '<span class="badge yellow">&#128311; 弱</span>'
    return '<span class="badge red">&#10060; 不显著</span>'

# ──────────────────────────────────────────────────
# 回测数据（2010-06 ~ 2026-05, 3800+ 交易日）
# ──────────────────────────────────────────────────
BT = {
    "vr_groups": [
        {"label":"超低<0.7","n":822,"pct":21.6,"fw_vol":0.80,"fw_ret":-0.19,"up":46},
        {"label":"低 0.7~1.0","n":1308,"pct":34.4,"fw_vol":1.18,"fw_ret":+0.11,"up":52},
        {"label":"正常 1.0~1.5","n":1295,"pct":34.0,"fw_vol":1.64,"fw_ret":+0.48,"up":54},
        {"label":"高 >1.5","n":382,"pct":10.0,"fw_vol":2.58,"fw_ret":+1.09,"up":61}
    ],
    "vol_thr": [
        {"name":"90%分位","thr":182,"n":381,"fw_vol":1.57,"fw_ret":+1.01,"up":57},
        {"name":"95%分位","thr":233,"n":191,"fw_vol":1.81,"fw_ret":+1.10,"up":59},
        {"name":"99%分位","thr":319,"n":39,"fw_vol":2.12,"fw_ret":+0.31,"up":49}
    ],
    "mean_fw_vol": 1.39,
    "mean_fw_ret": 0.27,
    "strategy": {
        "full": {"cum":279.8,"ann":13.4,"sharpe":0.44,"dd":-69.7},
        "high_vol": {"cum":153.6,"ann":10.2,"sharpe":0.36,"dd":-69.7},
        "vol_ratio": {"cum":128.5,"ann":9.4,"sharpe":0.33,"dd":-67.5}
    }
}

# ──────────────────────────────────────────────────
# 信号页面 HTML 生成
# ──────────────────────────────────────────────────

def page_html(title, emoji, desc, content):
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{emoji} {title} &mdash; CYB MDH</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<header>
  <a href="../index.html" class="back">&larr; 返回仪表盘</a>
  <h1>{emoji} {title}</h1>
  <p class="subtitle">{desc}</p>
</header>
{content}
<footer>
  CYB MDH Analysis &middot; baostock + 深交所 + 中证指数 &middot;
  {datetime.now().strftime("%Y-%m-%d %H:%M")}
</footer>
</div>
</body>
</html>'''

def render_granger(data):
    gr = data.get("garch_analysis", {}).get("granger_causality", {}).get("volume\u2192volatility", {})
    pv = gr.get("best_p_value", 1)
    lag = gr.get("best_lag", "?")
    sig = gr.get("significant", False)

    h = '<div class="kpi">'
    h += card(f"{pv:.4f}", f"Granger p值 (lag={lag})", "good" if sig else "bad")
    h += card("有效" if sig else "无效", "量→波动 Granger")
    h += card(lag, "最优滞后天数")
    h += '</div>'

    h += f'''<div class="box {"success" if sig else "warn"}">
      <b>检验结果：</b>{"显著" if sig else "不显著"}（p={pv:.4f}）。
      {"成交量包含预测波动率的信息。" if sig else "成交量对波动率没有显著预测力。"}
    </div>'''

    h += '<h2>回测事实</h2>'
    h += '<table><tr><th>策略</th><th>累计收益</th><th>年化收益</th><th>夏普</th><th>回撤</th></tr>'
    for k, n in [("满仓基准","full"), ("高量>90%→半仓","high_vol"), ("vol_ratio>1.5→半仓","vol_ratio")]:
        s = BT["strategy"][n]
        h += f'<tr><td>{k}</td><td>{s["cum"]:+.1f}%</td><td>{s["ann"]:+.1f}%</td><td>{s["sharpe"]:.2f}</td><td>{s["dd"]:.1f}%</td></tr>'
    h += '</table>'

    h += f'''<div class="box warn">
      <b>重要：</b>虽然 Granger 检验通过（量知道波），但实际回测中，用高量信号减仓反而导致收益大幅下降
      （满仓279.8% → 高量→半仓153.6%）。原因是高量区间恰好是创业板涨幅最大的时期，减仓反而错过了涨幅。
    </div>'''
    return h

def render_garchx(data):
    vv = data.get("garch_analysis", {}).get("volume_vs_turnover", {})
    vr = vv.get("volume_r2", 0)
    tr = vv.get("turnover_r2", 0)

    h = '<div class="kpi">'
    h += card(f"{vr:.4f}", "GARCH-X 成交量 R²", "warn")
    h += card(f"{tr:.4f}", "GARCH-X 换手率 R²", "bad")
    h += card("成交量", "更优预测变量")
    h += '</div>'

    h += f'''<div class="box info">
      <b>实际数据：</b>成交量解释力 R²=4.4%，换手率 1.0%。
      条件波动率中仅不到 5% 能被成交量解释。
    </div>'''

    # 阈值回测
    h += '<h2>回测事实：成交量阈值与波动率</h2>'
    h += '<table><tr><th>阈值</th><th>N</th><th>后5日波动</th><th>后5日收益</th><th>上涨</th></tr>'
    for t in BT["vol_thr"]:
        h += f'<tr><td>量>{t["name"]}(>{t["thr"]}亿)</td><td>{t["n"]}</td><td>{t["fw_vol"]:.2f}%</td><td>{t["fw_ret"]:+.2f}%</td><td>{t["up"]}%</td></tr>'
    h += f'<tr><td>全体均值</td><td>&mdash;</td><td>{BT["mean_fw_vol"]:.2f}%</td><td>{BT["mean_fw_ret"]:+.2f}%</td><td>&mdash;</td></tr>'
    h += '</table>'

    h += f'''<div class="box">
      <b>关键：</b>线性关系不存在（R²<5%），但阈值关系存在。
      量>90%分位后波动1.57%（均值1.39%），量>99%分位后2.12%。
      成交量预测波动率的本质是"极端事件触发"，不是日常线性关系。
    </div>'''
    return h

def render_pcr(data):
    p = data.get("pcr_analysis", {})
    bs = p.get("basic_stats", {})
    sigs = p.get("signals", {})

    h = '<div class="kpi">'
    h += card(f'{bs.get("vol_pcr_mean",0):.3f}', "PCR(量)均值")
    h += card(f'{bs.get("oi_pcr_mean",0):.3f}', "PCR(持仓)均值")
    h += card(f'{bs.get("vol_pcr_current",0):.3f}', "当前PCR(量)", "warn" if bs.get("vol_pcr_current",0) < 0.8 else "normal")
    h += '</div>'

    h += '<h2>回测事实：各阈值后5日收益</h2>'
    h += '<table><tr><th>信号</th><th>后5日</th><th>胜率</th><th>信号数</th></tr>'
    for k in ["低PCR(<0.7)_极度看涨", "高PCR(>1.2)_极度看跌", "近60日低PCR分位(<15%)", "低PCR(<0.8)_看涨", "高PCR(>1.0)_看跌"]:
        v = sigs.get(k, {})
        if isinstance(v, dict) and 'avg_5d_return' in v:
            r = v.get('avg_5d_return', 0)
            up = v.get('up_probability', 0)
            c = "color:#4ade80" if r > 1 else ("color:#f87171" if r < -0.5 else "color:#facc15")
            h += f'<tr><td>{k}</td><td style="{c}">{r:+.2f}%</td><td>{up:.0f}%</td><td>{v.get("signal_count",0)}</td></tr>'
    h += '</table>'

    h += '''<div class="box success">
      <b>唯一有效的方向信号：</b>PCR<0.7 后5日+2.44% 胜率60%。<br>
      高PCR(>1.2)看跌信号弱（-0.41%），PCR最佳应用是做多信号。
    </div>'''
    return h

def render_qvix(data):
    q = data.get("qvix_analysis", {})
    corr = q.get("corr_qvix_abs_ret", 0)
    hi = q.get("high_qvix_fwd_1d_vol", 0)
    all_m = q.get("all_mean_fwd_1d_vol", 1.3)
    lat = q.get("latest_qvix", 0)
    lpc = q.get("latest_percentile", 0)

    h = '<div class="kpi">'
    h += card(f"{corr:.2f}", "QVIX vs 实际波动 r", "good")
    h += card(f"{hi:.2f}%", "高QVIX次日波动", "warn")
    h += card(f"{lat:.0f}({lpc:.0f}%)", "当前QVIX", "bad" if lat > 35 else "good")
    h += '</div>'

    h += f'''<div class="box info">
      <b>不能判断方向：</b>高QVIX后次日上涨概率仅51%（抛硬币），r=0.12。<br>
      QVIX 只测幅不测向 — 适用于仓位管理，不适用于方向择时。
    </div>'''
    return h

def render_vol_ratio(data):
    vr90 = BT["vr_groups"][3]
    lo = BT["vr_groups"][0]

    h = '<div class="kpi">'
    h += card(f"{vr90['fw_vol']:.2f}%", "vol_ratio>1.5 后5日波动", "warn")
    h += card(f"{vr90['up']}%", "上涨概率", "good" if vr90['up'] > 55 else "warn")
    h += card(f"{lo['fw_ret']:+.2f}%", "vol_ratio<0.7 后5日收益", "bad")
    h += '</div>'

    h += '<h2>回测事实：vol_ratio 4档分组后5日表现</h2>'
    h += '<table><tr><th>分区</th><th>占比</th><th>后5日波动</th><th>后5日收益</th><th>上涨</th></tr>'
    for g in BT["vr_groups"]:
        h += f'<tr><td>vol_ratio {g["label"]}</td><td>{g["pct"]:.0f}%</td><td>{g["fw_vol"]:.2f}%</td><td>{g["fw_ret"]:+.2f}%</td><td>{g["up"]}%</td></tr>'
    h += '</table>'

    h += f'''<div class="box">
      <b>发现：</b>vol_ratio 高时，后5日收益反而 > 低时(高波区年化48%, 低波区-3%)。
      用 vol_ratio 做仓位调节会降低收益。<br>
      <b>有效用途：波动率估计</b> — 高>1.5时后5日波动2.58%，是超低波0.80%的3.2x。
    </div>'''
    return h

def render_dual(data):
    q = data.get("qvix_analysis", {})
    dual = q.get("dual_signal_fwd_1d_vol", 0)
    dual_n = q.get("dual_signal_count", 0)
    hi = q.get("high_qvix_fwd_1d_vol", 0)
    am = q.get("all_mean_fwd_1d_vol", 1.3)

    h = '<div class="kpi">'
    h += card(f"{dual:.2f}%", f"双重信号后次日波动({dual_n}次)", "bad")
    h += card(f"{dual/am:.1f}x" if am else "-", "vs 全体均值", "bad")
    h += card(f"{hi:.2f}%", "仅单信号(QVIX高)", "warn")
    h += '</div>'

    h += f'''<div class="box danger">
      <b>本框架中最有效的预警信号。</b>双重信号后次日波动{dual:.2f}%，
      是无信号的{dual/am:.1f}x。但仅出现{dual_n}次(3%时间)，样本量小(2022年起)。
    </div>'''

    # 策略回测嵌入
    h += '<h2>回测事实：基于波动率的仓位调节</h2>'
    h += '<table><tr><th>策略</th><th>累计</th><th>年化</th><th>夏普</th><th>回撤</th></tr>'
    for k, n in [("满仓基准","full"),("高量→半仓","high_vol"),("vol_ratio>1.5→半仓","vol_ratio")]:
        s = BT["strategy"][n]
        h += f'<tr><td>{k}</td><td>{s["cum"]:+.1f}%</td><td>{s["ann"]:+.1f}%</td><td>{s["sharpe"]:.2f}</td><td>{s["dd"]:.1f}%</td></tr>'
    h += '</table>'

    h += f'''<div class="box warn">
      <b>诚实结论：所有基于波动率减仓的简单策略都跑输满仓。</b><br>
      vol_ratio>1.5→半仓策略夏普0.33 vs 满仓0.44。<br>
      <b>原因：</b>高波动区间恰好是创业板涨幅最大的时期，减仓错过了更多收益。
    </div>'''
    return h

# ──────────────────────────────────────────────────
# 信号注册 & 页面生成
# ──────────────────────────────────────────────────

def render_qvix_strategy(data):
    fp = os.path.join(DATA_DIR, "qvix_strategy_curve.json")
    if not os.path.exists(fp):
        return "<div class='box warn'><b>策略回测数据尚未生成。</b></div>"
    with open(fp) as f:
        c = json.load(f)

    h = ''
    si = c.get('strategies', {})

    # === KPI 行 ===
    now_q = c['qvix'][-1] if c.get('qvix') else 0
    sp = os.path.join(DATA_DIR, "qvix_strategy.json")
    cur_strat = "无信号"
    cur_pct = 0
    if os.path.exists(sp):
        with open(sp) as f:
            s = json.load(f)
        cur_strat = s.get("current_signal", "无信号")
        cur_pct = s.get("qvix_pct_60", 0)

    sig_emoji = "💰" if cur_strat == "卖出期权(卖方)" else "🔥" if cur_strat == "买入期权" else "⏸️"
    sig_color = "warn" if cur_strat == "无信号" else "success"
    h += '<div class="kpi">'
    h += card(f"{now_q:.1f}%", "QVIX", "warn" if now_q > 30 else "good")
    h += card(f"{cur_pct:.0f}%", "60日分位", "warn" if cur_pct > 80 else "good")
    h += card(f"{sig_emoji} {cur_strat}", "当前策略信号", sig_color, fmt="s")
    h += '</div>'

    # === 策略说明 ===
    h += '''<div class="box info">
      <b>策略逻辑：</b><br>
      • <b>买方：</b>QVIX处于15-30%历史分位 → IV偏低 → 买入期权（赌波动率回升）。<br>
      • <b>卖方：</b>QVIX处于40-60%历史分位 → IV偏高 → 卖出期权（赚波动率溢价回归）。<br>
      • 所有卖方策略可叠加 <b>QVIX绝对值过滤</b> 和 <b>布林轨道（中轨上方）</b> 控制风险。
    </div>'''

    # === 策略对比表 ===
    h += '<h2>策略版本对比（2022-09 ~ 至今）</h2>'
    h += '<p><b>色块说明：</b>绿色=买方，黄色=卖方（下行敞口），灰色=基准。QVIX≥30完全消除了≥10%亏损。</p>'

    h += '<h3>买方策略</h3>'
    h += '<table><tr><th>策略</th><th>过滤条件</th><th>信号数</th><th>单笔均值</th><th>胜率</th><th>年化</th><th>夏普</th><th>最大回撤</th></tr>'
    for key, label in [('buy_pure','纯QVIX分位'), ('buy_mid_below','+中轨下方')]:
        st = si.get(key, {})
        if not st.get('n',0): continue
        h += f'<tr><td>买方</td><td>{label}</td><td>{st["n"]}</td>'
        h += f'<td style="color:#4ade80">{st["mean_ret"]:+.1f}%</td><td>{st["win_rate"]}%</td>'
        h += f'<td>{int(st["cagr"])}%</td><td>{st["sharpe"]:.2f}</td><td>{st["max_dd"]:.0f}pp</td></tr>'
    h += '</table>'

    h += '<h3>卖方策略（按风险过滤力度排序）</h3>'
    h += '<table><tr><th>策略</th><th>过滤条件</th><th>信号数</th><th>单笔均值</th><th>胜率</th><th>年化</th><th>夏普</th><th>最大回撤</th><th>亏损≥10%</th></tr>'
    sell_keys = [
        ('sell_pure','纯QVIX分位'), ('sell_mid_above','+中轨上方'),
        ('sell_qv25','QVIX≥25'), ('sell_qv25ma','QVIX≥25+中轨上'),
        ('sell_qv28','QVIX≥28'), ('sell_qv28ma','QVIX≥28+中轨上'),
        ('sell_qv30','QVIX≥30'), ('sell_qv30ma','QVIX≥30+中轨上'),
    ]
    for key, label in sell_keys:
        st = si.get(key, {})
        if not st.get('n',0): continue
        h += f'<tr><td>卖方</td><td>{label}</td><td>{st["n"]}</td>'
        h += f'<td style="color:#fbbf24">{st["mean_ret"]:+.1f}%</td><td>{st["win_rate"]}%</td>'
        h += f'<td>{int(st["cagr"])}%</td><td>{st["sharpe"]:.2f}</td><td>{st["max_dd"]:.0f}pp</td>'
        h += f'<td>{st["big_losses"]}次({st["big_loss_pct"]}%)</td></tr>'
    h += '<tr style="color:#64748b"><td>基准</td><td>全样本随机</td><td>805</td><td>+0.6%</td><td>47%</td><td>—</td><td>—</td><td>—</td><td>—</td></tr>'
    h += '</table>'

    # === 选择指南 ===
    h += '''<div class="box info">
      <b>🎯 卖方策略选择指南：</b><br>
      • <b>要信号多（每年~40笔）：</b>纯QVIX分位 → 但每10笔1笔亏>10%<br>
      • <b>要安全（0大亏）：</b>QVIX≥30+中轨上方 → 但每年仅~3笔<br>
      • <b>平衡点：</b>QVIX≥25（N=45，胜率89%，大亏概率6.7%）或 QVIX≥28（N=21，胜率95%）<br>
      • 所有QVIX≥30策略 <b>0笔亏损≥10%</b>，但信号稀少
    </div>'''

    # === 回测曲线图 ===
    h += '<h2>累计等权收益曲线</h2>'
    h += '<p>每笔信号独立等权加总（不计复利），vega=5x。<b>右侧Y轴</b>=QVIX（虚线）。</p>'

    dates_json = json.dumps([d[-5:] for d in c['dates']])
    qvix_json = json.dumps(c['qvix'])

    bp_nav = json.dumps(si.get('buy_pure',{}).get('nav',[1.0]))
    bm_nav = json.dumps(si.get('buy_mid_below',{}).get('nav',[1.0]))
    sp_nav = json.dumps(si.get('sell_pure',{}).get('nav',[1.0]))
    sm_nav = json.dumps(si.get('sell_mid_above',{}).get('nav',[1.0]))
    s25_nav = json.dumps(si.get('sell_qv25',{}).get('nav',[1.0]))
    s25m_nav = json.dumps(si.get('sell_qv25ma',{}).get('nav',[1.0]))
    s28_nav = json.dumps(si.get('sell_qv28',{}).get('nav',[1.0]))
    s28m_nav = json.dumps(si.get('sell_qv28ma',{}).get('nav',[1.0]))
    s30_nav = json.dumps(si.get('sell_qv30',{}).get('nav',[1.0]))
    s30m_nav = json.dumps(si.get('sell_qv30ma',{}).get('nav',[1.0]))

    h += f'''
<div id="buyChart" style="width:100%;height:400px;margin:12px 0;"></div>
<div id="sellBaseChart" style="width:100%;height:400px;margin:12px 0;"></div>
<div id="sellFilterChart" style="width:100%;height:400px;margin:12px 0;"></div>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<script>
(function(){{
  function chart(id,opt){{var c=echarts.init(document.getElementById(id));c.setOption(opt);window.addEventListener('resize',function(){{c.resize();}});}}
  var dates = {dates_json};
  var qv = {qvix_json};

  chart('buyChart', {{
    tooltip:{{trigger:'axis'}}, legend:{{textStyle:{{color:'#94a3b8'}}}},
    grid:{{left:'3%',right:'3%',bottom:'3%',containLabel:true}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'#64748b',fontSize:10,interval:40}}}},
    yAxis:[{{type:'value',name:'收益倍',nameTextStyle:{{color:'#94a3b8'}},axisLabel:{{color:'#94a3b8'}}}},
           {{type:'value',name:'QVIX%',nameTextStyle:{{color:'#94a3b8'}},axisLabel:{{color:'#94a3b8'}},splitLine:{{show:false}}}}],
    series:[
      {{name:'纯QVIX',type:'line',data:{bp_nav},smooth:true,symbol:'none',areaStyle:{{opacity:0.1}}}},
      {{name:'+中轨下方',type:'line',data:{bm_nav},smooth:true,lineStyle:{{color:'#34d399'}},symbol:'none',areaStyle:{{opacity:0.1}}}},
      {{name:'QVIX',type:'line',data:qv,smooth:true,lineStyle:{{width:0.5,color:'#60a5fa',type:'dashed'}},symbol:'none',yAxisIndex:1}}
    ]
  }});

  chart('sellBaseChart', {{
    tooltip:{{trigger:'axis'}}, legend:{{textStyle:{{color:'#94a3b8'}}}},
    grid:{{left:'3%',right:'3%',bottom:'3%',containLabel:true}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'#64748b',fontSize:10,interval:40}}}},
    yAxis:[{{type:'value',name:'收益倍',nameTextStyle:{{color:'#94a3b8'}},axisLabel:{{color:'#94a3b8'}}}},
           {{type:'value',name:'QVIX%',nameTextStyle:{{color:'#94a3b8'}},axisLabel:{{color:'#94a3b8'}},splitLine:{{show:false}}}}],
    series:[
      {{name:'卖方纯QVIX',type:'line',data:{sp_nav},smooth:true,lineStyle:{{color:'#fbbf24',width:1}},symbol:'none',areaStyle:{{opacity:0.05}}}},
      {{name:'+中轨上方',type:'line',data:{sm_nav},smooth:true,lineStyle:{{color:'#fb923c',width:2}},symbol:'none',areaStyle:{{opacity:0.1}}}},
      {{name:'QVIX',type:'line',data:qv,smooth:true,lineStyle:{{width:0.5,color:'#60a5fa',type:'dashed'}},symbol:'none',yAxisIndex:1}}
    ]
  }});

  chart('sellFilterChart', {{
    tooltip:{{trigger:'axis'}}, legend:{{textStyle:{{color:'#94a3b8'}}}},
    grid:{{left:'3%',right:'3%',bottom:'3%',containLabel:true}},
    xAxis:{{type:'category',data:dates,axisLabel:{{color:'#64748b',fontSize:10,interval:40}}}},
    yAxis:[{{type:'value',name:'收益倍',nameTextStyle:{{color:'#94a3b8'}},axisLabel:{{color:'#94a3b8'}}}},
           {{type:'value',name:'QVIX%',nameTextStyle:{{color:'#94a3b8'}},axisLabel:{{color:'#94a3b8'}},splitLine:{{show:false}}}}],
    series:[
      {{name:'QVIX≥25',type:'line',data:{s25_nav},smooth:true,lineStyle:{{width:1,color:'#facc15'}},symbol:'none',areaStyle:{{opacity:0.05}}}},
      {{name:'QVIX≥25+中轨',type:'line',data:{s25m_nav},smooth:true,lineStyle:{{width:1,color:'#f97316'}},symbol:'none'}},
      {{name:'QVIX≥28',type:'line',data:{s28_nav},smooth:true,lineStyle:{{width:1,color:'#f87171'}},symbol:'none'}},
      {{name:'QVIX≥28+中轨',type:'line',data:{s28m_nav},smooth:true,lineStyle:{{width:1.5,color:'#ef4444'}},symbol:'none'}},
      {{name:'QVIX≥30🏆',type:'line',data:{s30_nav},smooth:true,lineStyle:{{width:2,color:'#dc2626'}},symbol:'none'}},
      {{name:'QVIX≥30+中轨',type:'line',data:{s30m_nav},smooth:true,lineStyle:{{width:2,color:'#991b1b',type:'dotted'}},symbol:'none'}},
      {{name:'QVIX',type:'line',data:qv,smooth:true,lineStyle:{{width:0.5,color:'#60a5fa',type:'dashed'}},symbol:'none',yAxisIndex:1}}
    ]
  }});
}})();
</script>
'''

    # === 最近信号明细 ===
    if os.path.exists(sp):
        with open(sp) as f:
            s = json.load(f)
        h += '<h3>最近5次买方信号</h3>'
        h += '<table><tr><th>日期</th><th>QVIX</th><th>分位</th><th>10日后ΔQVIX</th><th>期权收益</th></tr>'
        for r in s.get("recent_buy_signals", [])[-5:]:
            dq = r.get("fwd_delta_qvix", "--") or "--"
            op = r.get("opt_ret", "--") or "--"
            col = 'color:#4ade80' if (isinstance(op,(int,float)) and op>0) else 'color:#f87171' if (isinstance(op,(int,float)) and op<0) else ''
            h += f'<tr><td>{r["date"]}</td><td>{r["qvix"]}%</td><td>{r["pct"]}%</td><td>{dq}</td><td style="{col}">{op}</td></tr>'
        h += '</table>'

    h += f'''<div class="box warn">
      <b>⚠️ 局限：</b>期权收益基于简化模型（vega=5x），未计复利和交易成本。QVIX数据仅2022年9月起（874个交易日）。
      QVIX≥30过滤后样本仅10-18笔，统计显著性有限。<b>实盘必须设置止损</b>。
    </div>'''
    return h

def render_lottery(data):
    """末日彩票策略 - 布林下轨+超跌买入末日call"""
    jp = os.path.join(DATA_DIR, "lottery_strategy.json")
    if not os.path.exists(jp):
        return '<div class="box warn">数据文件未生成，请先运行数据分析脚本。</div>'
    with open(jp) as f:
        s = json.load(f)
    
    s1 = s["strategy1"]
    s2 = s["strategy2"]
    st6 = s1["stats_6d"]
    st10 = s1["stats_10d"]
    st_simple = s2["stats_6d"]
    
    h = f'''
<div class="box info">
  <b>🎯 核心思路：</b>当创业板跌到布林300下轨附近(碰触或接近)，且最近20日跌幅>8%时，买入6天后到期的平值call。
  超跌+到技术支撑位 → 反弹概率高，末日期权杠杆放大收益。
</div>

<div class="box">
  <b>📐 期权定价假设：</b>平值期权价格 ≈ 0.4 × IV × √(T/252) × S，
  IV固定取26%（QVIX历史均值），T=6天。期权费约ETF价格的{round(s['meta']['prem_ratio']*100,1)}%。
  如ETF=3000元，每张期权约&#165;{round(s['meta']['prem_ratio']*3000)}。
  <br><br>
  <b>⚠️ 说明：</b>回测使用固定IV=26%，实际IV会变动。末日归零风险高(每3次中约1次归零)。
  每笔不超过账户总资产的1-2%。
</div>

<h2>策略1：布林下轨 + 20日跌>8%</h2>
<p>信号区间：{s['meta']['date_range']} &middot; 共{len(s1['signals'])}次信号</p>

<h3>6天末日call 统计</h3>
<div class="kpi">
  <div class="kpi-card"><div class="kpi-val">{st6["n"]}</div><div class="kpi-label">总信号数</div></div>
  <div class="kpi-card {"good" if st6["win_rate"]>=50 else "bad"}"><div class="kpi-val">{st6["win_rate"]}%</div><div class="kpi-label">胜率</div></div>
  <div class="kpi-card good"><div class="kpi-val">{st6["avg_win_pct"]:.0f}%</div><div class="kpi-label">平均盈利</div></div>
  <div class="kpi-card bad"><div class="kpi-val">-{st6["avg_loss_pct"]:.0f}%</div><div class="kpi-label">平均亏损</div></div>
  <div class="kpi-card good"><div class="kpi-val">{st6["rr"]}x</div><div class="kpi-label">盈亏比(R/R)</div></div>
  <div class="kpi-card {"good" if st6["exp_per_100"]>0 else "bad"}"><div class="kpi-val">{st6["exp_per_100"]:.0f}</div><div class="kpi-label">期望值/100元</div></div>
  <div class="kpi-card warn"><div class="kpi-val">{st6["zero_rate"]:.0f}%</div><div class="kpi-label">归零率(废纸)</div></div>
</div>

<h3>收益多倍分布</h3>
<table>
  <tr><th>收益</th><th>&gt;1x</th><th>&gt;2x</th><th>&gt;3x</th><th>&gt;5x</th></tr>
  <tr><td>6天末日call</td>
    <td>{st6["pct_1x"]:.0f}%</td>
    <td>{st6["pct_2x"]:.0f}%</td>
    <td>{st6["pct_3x"]:.0f}%</td>
    <td>{st6["pct_5x"]:.0f}%</td></tr>
  <tr><td>10天末日call</td>
    <td>{st10["pct_1x"]:.0f}%</td>
    <td>{st10["pct_2x"]:.0f}%</td>
    <td>{st10["pct_3x"]:.0f}%</td>
    <td>{st10["pct_5x"]:.0f}%</td></tr>
</table>

<h3>10天末日call 对比</h3>
<div class="kpi">
  <div class="kpi-card good"><div class="kpi-val">{st10["win_rate"]}%</div><div class="kpi-label">胜率</div></div>
  <div class="kpi-card good"><div class="kpi-val">{st10["avg_win_pct"]:.0f}%</div><div class="kpi-label">平均盈利</div></div>
  <div class="kpi-card good"><div class="kpi-val">{st10["rr"]}x</div><div class="kpi-label">盈亏比</div></div>
  <div class="kpi-card good"><div class="kpi-val">{st10["exp_per_100"]:.0f}</div><div class="kpi-label">期望值/100元</div></div>
</div>

<h2>策略2：仅20日跌>10%（简化版）</h2>
<p>不需要布林信号，只要创业板20日内跌超10%就买入末日call。N={s2['signal_count']}次。</p>
<div class="kpi">
  <div class="kpi-card"><div class="kpi-val">{st_simple["n"]}</div><div class="kpi-label">总信号数</div></div>
  <div class="kpi-card {"good" if st_simple["win_rate"]>=50 else "bad"}"><div class="kpi-val">{st_simple["win_rate"]}%</div><div class="kpi-label">胜率</div></div>
  <div class="kpi-card good"><div class="kpi-val">{st_simple["avg_win_pct"]:.0f}%</div><div class="kpi-label">平均盈利</div></div>
  <div class="kpi-card good"><div class="kpi-val">{st_simple["rr"]}x</div><div class="kpi-label">盈亏比</div></div>
  <div class="kpi-card {"good" if st_simple["exp_per_100"]>0 else "bad"}"><div class="kpi-val">{st_simple["exp_per_100"]:.0f}</div><div class="kpi-label">期望值/100元</div></div>
  <div class="kpi-card warn"><div class="kpi-val">{st_simple["zero_rate"]:.0f}%</div><div class="kpi-label">归零率</div></div>
</div>

<h2>📅 历史信号明细（策略1）</h2>
<table><tr><th>日期</th><th>收盘价</th><th>布林位</th><th>20d跌</th><th>6d后收益</th><th>20d后收益</th><th>60d后收益</th></tr>'''
    for sig in s1["signals"]:
        f5 = f'{sig["fwd5_ret"]:+.0f}%' if sig["fwd5_ret"] is not None else '--'
        f20 = f'{sig["fwd20_ret"]:+.0f}%' if sig["fwd20_ret"] is not None else '--'
        f60 = f'{sig["fwd60_ret"]:+.0f}%' if sig["fwd60_ret"] is not None else '--'
        c5 = 'color:#4ade80' if (sig.get("fwd5_ret") or 0) > 0 else 'color:#f87171' if (sig.get("fwd5_ret") or 0) < 0 else ''
        h += f'<tr><td>{sig["date"]}</td><td>{sig["close"]:.0f}</td><td>{sig["bb300_pos"]:.0f}%</td><td>{sig["ret_20d"]:+.0f}%</td><td style="{c5}">{f5}</td><td>{f20}</td><td>{f60}</td></tr>'
    
    h += '''</table>

<h2>🏷️ 不同行权价 × 到期日对比</h2>
<p>同样信号下，选择不同行权价的末日期权结果完全不同。时间价值少（实值）不一定更好。</p>
<table>
  <tr><th>行权价</th><th>到期</th><th>权利金%</th><th>归零%</th><th>胜率%</th><th>avg赚%</th><th>avg亏%</th><th>R/R</th><th>期望/100</th></tr>'''
    for r in s.get("strike_comparison", []):
        css = 'good' if r['rr'] >= 2 else 'normal'
        h += f'<tr><td>{r["strike"]}</td><td>{r["days"]}d</td><td>{r["prem_pct"]:.1f}%</td><td>{r["zero_pct"]:.0f}%</td><td>{r["win_rate"]:.0f}%</td><td>+{r["avg_win_pct"]:.0f}%</td><td>-{r["avg_loss_pct"]:.0f}%</td><td style="font-weight:bold;color:#{"4ade80" if r["rr"]>=3 else "facc15" if r["rr"]>=1 else "f87171"}">{r["rr"]}x</td><td style="font-weight:bold;color:#{"4ade80" if r["exp_per_100"]>0 else "f87171"}">{r["exp_per_100"]:+.0f}</td></tr>'''

    h += '''</table>

<div class="box warn">
  <b>💡 关键发现：</b><br><br>
  <b>时间价值越少（实值）≠ 越好。</b><br>
  ● ITM90%行权价（低10%）：权利金10.8%，归零仅2%，但盈利空间受限，R/R仅0.9x<br>
  ● ATM平值：权利金1.5%，R/R 2.9x，最均衡的选择<br>
  ● OTM103%轻度虚值（高3%）：权利金仅0.3%，R/R 8.5x，期望+264元/100元 — 最高期望<br>
  ● OTM110%深度虚值：权利金0.1%，但归零率98%，期望为负<br><br>
  <b>推荐：轻度虚值(OTM103%) + 21天到期</b> — R/R 12.9x，期望+685元/100元，且归零率仅39%<br>
  或<b>平值ATM + 10天到期</b> — 最稳定正期望，R/R 3.0x，期望+108元/100元
</div>

<div class="box success">
  <b>✅ 总结：</b>布林下轨+超跌买入末日call是<u>正期望策略</u>（期望+97元/100元）。
  每3次中约1次归零，但每次中奖平均赚237%。适合小仓位（1-2%账户）长期执行。
  <br><br>
  <b>⚠️ 风险：</b>末日归零率高(31%)，需连续多次不中后有止损意识。
  实际操作中IV会变化，期权价格会有滑点。
</div>'''
    return h

def render_eruption_honesty(data):
    """爆发事件诚实分类"""
    jp = os.path.join(DATA_DIR, "eruption_honesty.json")
    if not os.path.exists(jp):
        return '<div class="box warn">数据文件未生成。</div>'
    with open(jp) as f:
        t = json.load(f)
    
    h = '''
<div class="box info">
  <b>⛰️ 为什么做这个页面：</b>我们花了很长时间找"爆发信号"，结论是：<b>79%的爆发在技术上不可预测</b>。
  这不是代码没写好，而是市场本质。<br><br>
  <b>诚实比过拟合重要。</b>我们只标注已知可靠的模式，不编造公式。
</div>

<div class="box danger" style="border-left-color:#ef4444">
  <b>核心发现：</b>创业板历史上47次爆发事件（未来20d>20%或10d>12%）中，
  只有<b>4次(9%)</b>可被彩票策略(布林下轨+超跌)稳定识别，
  <b>2次(4%)</b>有模糊信号，
  <b>41次(87%)</b>完全无法通过量价信号提前预测。
</div>
'''
    h += '<h2>📊 分类汇总</h2>'
    h += f'<p>总爆发事件: {t["meta"]["total_events"]} &middot; 数据区间: {t["meta"]["date_range"]}</p>'
    h += f'<p style="font-size:0.85em;color:#94a3b8;margin-top:-8px;">{t["meta"]["summary"]}</p>'
    
    cat_styles = {
        '可预测(彩票)': '#4ade80',
        '低置信可预测': '#facc15',
        '部分可预测': '#fb923c',
        '不可预测': '#f87171',
    }
    
    h += '<table><tr><th>类别</th><th>次数</th><th>占比</th><th>前20d</th><th>前vol_ratio</th><th>前布林位</th><th>涨幅</th><th>说明</th></tr>'
    for cat_key, color in [('可预测(彩票)','#4ade80'),('低置信可预测','#facc15'),('不可预测','#f87171')]:
        c = t['categories'].get(cat_key)
        if not c: continue
        ev = c['events']
        r20 = c.get('mean_ret20d',0)
        bb = c.get('mean_bb',0)
        pk = c.get('mean_peak',0)
        note = ''
        if cat_key == '可预测(彩票)': note = '布林下轨+超跌≥8% → 彩票策略可用'
        elif cat_key == '不可预测': note = '中上轨横盘或趋势中加速，无技术预警'
        elif cat_key == '低置信可预测': note = '有部分指标指向但信号弱不可靠'
        h += f'<tr><td style="color:{color};font-weight:bold">{cat_key}</td><td>{c["count"]}</td><td>{c.get("pct","?")}%</td><td>{r20:+.1f}%</td><td></td><td>{bb}%</td><td>+{pk:.0f}%</td><td style="font-size:0.85em;color:#94a3b8">{note}</td></tr>'
    
    h += '</table>'
    
    # 可预测事件列表
    h += '''<h2>✅ 可预测的爆发</h2>
<p>彩票策略(布林下轨+20d跌>8%)能在爆发前发出信号的案例：</p>
<table><tr><th>日期</th><th>前收盘</th><th>峰值</th><th>涨幅</th><th>前20d</th><th>前vol</th><th>前布林%</th></tr>'''
    for ev in t['categories'].get('可预测(彩票)',{}).get('events',[]):
        h += f'<tr><td>{ev["start_date"]}</td><td>{ev["pre_close"]}</td><td>{ev["peak"]}</td><td style="color:#4ade80">+{ev["peak_ret"]:.0f}%</td><td>{ev.get("pre_ret20d") or "?"}</td><td>{ev.get("pre_vol_ratio") or "?"}</td><td>{ev.get("pre_bb_pos") or "?"}</td></tr>'
    
    h += '''</table>

<h2>❌ 不可预测的爆发</h2>
<p>这些爆发在量价指标上没有提前信号——前20d平均上涨+4.4%，布林中上轨(81%)，成交量正常(1.13x)：</p>
<table><tr><th>日期</th><th>前收盘</th><th>峰值</th><th>涨幅</th><th>前20d</th><th>前vol</th><th>前布林%</th></tr>'''
    for ev in t['categories'].get('不可预测',{}).get('events',[]):
        h += f'<tr><td>{ev["start_date"]}</td><td>{ev["pre_close"]}</td><td>{ev["peak"]}</td><td style="color:#f87171">+{ev["peak_ret"]:.0f}%</td><td>{ev.get("pre_ret20d") or "?"}</td><td>{ev.get("pre_vol_ratio") or "?"}</td><td>{ev.get("pre_bb_pos") or "?"}</td></tr>'
    
    h += '''</table>

<div class="box warn">
  <b>⚠️ 诚实声明：</b><br>
  ● 彩票策略只覆盖了9%的爆发事件（4/47）<br>
  ● 87%的爆发发生在布林中上轨+前20d上涨中（趋势加速/事件驱动）<br>
  ● 对这些爆发的任何"信号公式"都是过拟合，没有统计意义<br>
  ● 如果一个人声称能找到"所有爆发点"，那他一定在说谎或将发生过拟合<br>
  ● <b>承认不可预测，本身就是一种预测</b>——知道什么时候该空仓等待
</div>'''
    return h

def render_thermometer(data):
    """市场温度计 — 状态分类系统"""
    tp = os.path.join(DATA_DIR, "thermometer.json")
    if not os.path.exists(tp):
        return '<div class="box warn">数据文件未生成，请先运行数据分析脚本。</div>'
    with open(tp) as f:
        t = json.load(f)
    
    cur = t['current']
    re = t['ready_to_erupt']
    
    state_colors = {'死寂':'#64748b','平静':'#60a5fa','躁动':'#facc15','异动':'#fb923c','预备爆发':'#f97316','风暴':'#f87171'}
    sc = state_colors.get(cur['state'], '#60a5fa')
    
    h = f'''
<div class="box info">
  <b>🌡️ 核心理念：</b>市场不是随机游走，而是在不同状态间转换——平静、躁动、异动、预备爆发、风暴。
  状态分类基于两个关键维度：<b>相对成交量(vol_ratio)</b> 和 <b>短期波动率HV_10的近3月分位</b>。
  <br><br>
  分类规则：
  ● <b>风暴</b> — HV_10 > 40%年化
  ● <b>异动</b> — vol_ratio > 2.0
  ● <b>预备爆发</b> — vol_ratio > 1.5 且 HV_10 < 近3月50%分位
  ● <b>躁动</b> — vol_ratio > 1.2
  ● <b>死寂</b> — vol_ratio < 0.6 且 HV_10 < 20%
  ● <b>平静</b> — 其他
</div>

<h2>📡 当前市场状态</h2>
<div class="qt">
  <div class="qtc" style="border-color:{sc}">
    <div class="qtv" style="color:#60a5fa">{cur['state']}</div>
    <div class="qtl">当前状态 ({cur['date']})</div>
  </div>
  <div class="qtc" style="border-color:#60a5fa">
    <div class="qtv" style="color:#60a5fa">{t['meta']['total_dates']}</div>
    <div class="qtl">总样本天数</div>
  </div>
  <div class="qtc" style="border-color:#60a5fa">
    <div class="qtv" style="color:#facc15">{cur['vol_ratio']}x</div>
    <div class="qtl">相对成交量</div>
  </div>
  <div class="qtc" style="border-color:#60a5fa">
    <div class="qtv" style="color:#facc15">{cur['hv_10']:.0f}%</div>
    <div class="qtl">HV_10(年化)</div>
  </div>
  <div class="qtc" style="border-color:#60a5fa">
    <div class="qtv" style="color:#facc15">{cur['hv_10_rank_3m']:.0f}%</div>
    <div class="qtl">HV_10近3月分位</div>
  </div>
</div>

<h2>📊 各状态收益特征 (2010-2026)</h2>
<p>每个状态下买入并持有不同期限的平均收益。</p>
<table>
  <tr><th>状态</th><th>占比</th><th>5d均值</th><th>5d胜率</th><th>10d均值</th><th>10d胜率</th><th>20d均值</th><th>彩票>20%</th></tr>'''
    for r in t['states']:
        color = state_colors.get(r['state'], '#60a5fa')
        h += f'<tr><td style="color:{color};font-weight:bold">{r["state"]}</td>'
        h += f'<td>{r["n"]} ({r["n"]/t["meta"]["total_dates"]*100:.0f}%)</td>'
        h += f'<td style="color:{"#4ade80" if r["fwd5_mean"]>0 else "f87171"}">{r["fwd5_mean"]:+.1f}%</td>'
        h += f'<td>{r["fwd5_win"]:.0f}%</td>'
        h += f'<td style="color:{"#4ade80" if r["fwd10_mean"]>0 else "f87171"}">{r["fwd10_mean"]:+.1f}%</td>'
        h += f'<td>{r["fwd10_win"]:.0f}%</td>'
        h += f'<td style="color:{"#4ade80" if r["fwd20_mean"]>0 else "f87171"}">{r["fwd20_mean"]:+.1f}%</td>'
        h += f'<td>{r["fwd20_lotto"]:.0f}%</td></tr>'
    
    h += f'''</table>

<h2>🔥 核心状态：预备爆发</h2>
<div class="box warn" style="border-left-color:#f97316">
  <b>定义：</b>成交量突然放大(vol_ratio > 1.5)，但短期波动率仍处近3月低位(HV_10 < 50%分位)。<br>
  这意味着：<u>市场开始放量但波动还未跟上，平静即将被打破</u>。
</div>

<div class="kpi">
  <div class="kpi-card warn"><div class="kpi-val">{re["n"]}次</div><div class="kpi-label">总信号 ({re["pct"]}%)</div></div>
  <div class="kpi-card {"good" if re["fwd5_mean"]>0 else "bad"}"><div class="kpi-val">{re["fwd5_mean"]:+.1f}%</div><div class="kpi-label">未来5d均值</div></div>
  <div class="kpi-card"><div class="kpi-val">{re["fwd5_win"]:.0f}%</div><div class="kpi-label">5d胜率</div></div>
  <div class="kpi-card"><div class="kpi-val">{re["fwd10_mean"]:+.1f}%</div><div class="kpi-label">未来10d均值</div></div>
  <div class="kpi-card"><div class="kpi-val">{re["fwd10_win"]:.0f}%</div><div class="kpi-label">10d胜率</div></div>
  <div class="kpi-card"><div class="kpi-val">{re["fwd20_mean"]:+.1f}%</div><div class="kpi-label">未来20d均值</div></div>
  <div class="kpi-card warn"><div class="kpi-val">{re["fwd20_gt10"]:.0f}%</div><div class="kpi-label">>10%概率</div></div>
  <div class="kpi-card warn"><div class="kpi-val">{re["fwd20_gt20"]:.0f}%</div><div class="kpi-label">>20%彩票</div></div>
</div>

<div class="box success">
  <b>💡 实战用法：</b><br>
  ● 处于<b>预备爆发</b>状态 → 关注期权买方机会（波动率即将放大的先兆）<br>
  ● 处于<b>风暴</b>状态 → 彩票概率提升（20d>20%概率6%），可配合布林下轨+超跌执行末日彩票策略<br>
  ● 处于<b>平静</b>状态 → 无信号，等待<br>
  ● 处于<b>躁动</b>状态 → 小幅正收益趋势，可小仓做多<br><br>
  <b>注意：</b>预备爆发信号仅45次(1.2%概率)，信号稀少但方向清晰。<br>
  <b>当前状态：{cur["state"]}</b> → 当前 {"有" if cur["state"]=="预备爆发" or cur["state"]=="风暴" else "无"}交易信号
</div>

<h2>📅 最近预备爆发信号</h2>
<table><tr><th>日期</th><th>收盘价</th><th>状态</th><th>vol_ratio</th><th>HV_10</th><th>HV_10分位</th><th>未来10d收益</th></tr>'''
    for sig in t['last_signals'][-15:]:
        f10 = f'{sig["fwd10_ret"]:+.1f}%' if sig.get("fwd10_ret") is not None else '--'
        c10 = 'color:#4ade80' if (sig.get("fwd10_ret") or 0) > 0 else 'color:#f87171'
        h += f'<tr><td>{sig["date"]}</td><td>{sig["close"]}</td><td style="color:{state_colors.get(sig["state"],"#60a5fa")}">{sig["state"]}</td><td>{sig["vol_ratio"]}x</td><td>{sig["hv_10"]:.0f}%</td><td>{sig["hv_10_rank"]:.0f}%</td><td style="{c10}">{f10}</td></tr>'
    
    h += '</table>'
    return h



def render_divergence(data):
    """背离信号检测 — 多维度恐慌背离/机构背离"""
    dp = os.path.join(DATA_DIR, "divergence_signal.json")
    if not os.path.exists(dp):
        return '<div class="box warn">数据文件未生成，请先运行分析脚本。</div>'
    with open(dp) as f:
        d = json.load(f)
    cur = d['current']
    ec = []
    if cur.get('hv_panic'): ec.append("📉 HV恐慌背离")
    if cur.get('qvix_panic'): ec.append("⚠️ QVIX恐慌背离")
    if cur.get('pcr_panic'): ec.append("📊 PCR恐慌背离")
    if cur.get('oi_gt_vol'): ec.append("🏛️ OI>>vol机构背离")
    if cur.get('vol_gt_oi'): ec.append("😱 vol>>OI散户恐慌")
    if cur.get('hv_accel'): ec.append("⚡ 波动率加速")
    now_signals = '、'.join(ec) if ec else '无活跃背离信号'
    now_color = '#f87171' if cur.get('panic_score',0) >= 3 else '#facc15' if cur.get('panic_score',0) >= 1 else '#4ade80'
    h = f'''
<div class="box info">
  <b>🎯 核心理念：</b>当价格下跌但波动率/PCR等指标反向上升时，称为"背离"。
  背离信号捕捉市场情绪极端化时刻——恐慌或机构对冲，通常预示后续反转。
</div>
<h2>📡 当前背离状态 ({cur.get("date","")})</h2>
<div class="qt">
  <div class="qtc" style="border-color:{now_color}">
    <div class="qtv" style="color:{now_color}">{cur.get("panic_score",0)}/5</div>
    <div class="qtl">恐慌分数</div>
  </div>
  <div class="qtc" style="border-color:#60a5fa">
    <div class="qtv" style="font-size:1em;color:#60a5fa">{now_signals[:40]}</div>
    <div class="qtl">活跃背离信号</div>
  </div>
</div>
<p style="color:{now_color};font-weight:bold;text-align:center;">{now_signals}</p>
<h2>🔍 背离信号分类回测</h2>
<p>每个信号触发后未来20日收益统计。</p>'''
    sig_order = [
        ("oi_gt_vol", "OI>>vol(机构背离)", "#8b5cf6", "机构大量持有卖权远超成交量：防御性对冲"),
        ("hv_panic", "HV恐慌背离", "#f87171", "HV_10分位短期急升同时价格下跌"),
        ("hv_accel", "波动率加速", "#fb923c", "短期HV分位 > 长期HV分位+20pp"),
        ("qvix_panic", "QVIX恐慌背离", "#f97316", "隐含波动率上升同时价格下跌"),
        ("vol_gt_oi", "vol>>OI(散户恐慌)", "#e879f9", "成交量PCR远超持仓量PCR：散户恐慌买入认沽"),
        ("pcr_panic", "PCR恐慌背离", "#a78bfa", "PCR成交量短期急升同时价格下跌"),
    ]
    for sk, sname, scol, sdesc in sig_order:
        if sk not in d["signals"]: continue
        s = d["signals"][sk]
        h20 = s["fwd_holding"].get("20d", {})
        m = h20.get("mean", 0)
        wr = h20.get("win_rate", 50)
        gt10 = h20.get("gt10_pct", 0)
        h += f'''
<div class="box" style="border-left-color:{scol}">
  <h3 style="color:{scol}">{sname}</h3>
  <p style="color:#94a3b8;">{sdesc}（总N={s["n"]}次）</p>
  <div class="kpi">
    <div class="kpi-card good"><div class="kpi-val">{s["n"]}</div><div class="kpi-label">总信号</div></div>
    <div class="kpi-card {"good" if m>0 else "bad"}"><div class="kpi-val">{m:+.1f}%</div><div class="kpi-label">20d均值</div></div>
    <div class="kpi-card {"good" if wr>=55 else "normal"}"><div class="kpi-val">{wr:.0f}%</div><div class="kpi-label">20d胜率</div></div>
    <div class="kpi-card warn"><div class="kpi-val">{gt10:.0f}%</div><div class="kpi-label">>10%概率</div></div>
  </div>
  <p>'''
        for dk in ["5d","10d","20d","30d"]:
            if dk in s["fwd_holding"]:
                hd = s["fwd_holding"][dk]
                c = "#4ade80" if hd["mean"]>0 else "#f87171"
                h += f' <span style="color:{c}">{dk}: {hd["mean"]:+.1f}%</span>'
        h += '</p></div>'
    
    h += '''
<h2>📅 近期背离事件</h2>
<table><tr><th>日期</th><th>收盘</th><th>背离信号</th><th>分数</th><th>之后20d</th></tr>'''
    for ev in d.get("recent_events", [])[::-1][-20:]:
        sig_str = " + ".join(ev["signals"])
        f20 = f'{ev["fwd20"]:+.0f}%' if ev.get("fwd20") is not None else '--'
        c20 = '#4ade80' if (ev.get("fwd20") or 0) > 0 else '#f87171' if (ev.get("fwd20") or 0) < 0 else '#94a3b8'
        h += f'<tr><td>{ev["date"]}</td><td>{ev["close"]:.0f}</td><td style="color:#facc15;font-size:0.9em">{sig_str}</td><td>{ev["score"]}</td><td style="color:{c20}">{f20}</td></tr>'
    h += '''</table>

<h2>🔬 广义背离深入回测（5日趋势方向相反）</h2>
<p>核心逻辑：价格趋势与指标趋势方向相反。以下是全样本(2018-2026)所有背离类型的对比。</p>

<h3>① 单类背离强度排行 (20日持有)</h3>
<table>
  <tr><th>背离类型</th><th>N</th><th>5d</th><th>10d</th><th>10d胜率</th><th>20d</th><th>20d胜率</th><th>30d</th><th>>10%</th></tr>
  <tr style="background:#1e293b"><td style="color:#8b5cf6;font-weight:bold">OI>>vol（机构对冲）</td><td>103</td><td style="color:#4ade80">+1.6%</td><td style="color:#4ade80">+2.8%</td><td>69%</td><td style="color:#4ade80">+4.2%</td><td>64%</td><td style="color:#4ade80">+5.4%</td><td>27%</td></tr>
  <tr><td style="color:#fb923c;font-weight:bold">QVIX涨+价跌（隐波恐慌）</td><td>142</td><td style="color:#4ade80">+0.7%</td><td style="color:#4ade80">+2.1%</td><td>61%</td><td style="color:#4ade80">+2.7%</td><td>55%</td><td style="color:#4ade80">+2.9%</td><td>21%</td></tr>
  <tr><td style="color:#f87171;font-weight:bold">量跌+价涨（缩量上涨）</td><td>451</td><td style="color:#4ade80">+0.5%</td><td style="color:#4ade80">+1.3%</td><td>59%</td><td style="color:#4ade80">+2.4%</td><td>58%</td><td style="color:#4ade80">+3.3%</td><td>25%</td></tr>
  <tr><td style="color:#a78bfa;font-weight:bold">PCR涨+价跌（恐慌买put）</td><td>186</td><td style="color:#f87171">-0.0%</td><td style="color:#4ade80">+0.2%</td><td>47%</td><td style="color:#4ade80">+1.1%</td><td>47%</td><td style="color:#4ade80">+1.6%</td><td>17%</td></tr>
  <tr><td style="color:#f97316;font-weight:bold">量涨+价跌（放量恐慌）</td><td>393</td><td style="color:#4ade80">+0.2%</td><td style="color:#4ade80">+0.4%</td><td>50%</td><td style="color:#4ade80">+1.0%</td><td>51%</td><td style="color:#4ade80">+2.4%</td><td>22%</td></tr>
  <tr><td style="color:#f87171;font-weight:bold">HV涨+价跌（波动率恐慌）</td><td>943</td><td style="color:#f87171">-0.0%</td><td style="color:#4ade80">+0.5%</td><td>53%</td><td style="color:#4ade80">+0.9%</td><td>51%</td><td style="color:#4ade80">+1.6%</td><td>19%</td></tr>
</table>

<h3>② 叠加背离（同时有N种指标在背离）</h3>
<table>
  <tr><th>叠加数</th><th>N</th><th>占比</th><th>10d</th><th>20d</th><th>30d</th><th>45d</th><th>60d</th></tr>
  <tr><td style="color:#4ade80">&#8593; 空头背离&#8805;1</td><td>1228</td><td>31.9%</td><td style="color:#4ade80">+0.3%</td><td style="color:#4ade80">+0.7%</td><td style="color:#4ade80">+1.6%</td><td style="color:#4ade80">+2.2%</td><td style="color:#4ade80">+2.7%</td></tr>
  <tr><td style="color:#facc15">&#8593; 空头背离&#8805;2</td><td>347</td><td>9.0%</td><td style="color:#4ade80">+1.1%</td><td style="color:#4ade80">+1.9%</td><td style="color:#4ade80">+2.4%</td><td style="color:#4ade80">+3.3%</td><td style="color:#4ade80">+4.0%</td></tr>
  <tr><td style="color:#f97316">&#8593; 空头背离&#8805;3</td><td>70</td><td>1.8%</td><td style="color:#4ade80">+2.0%</td><td style="color:#4ade80">+4.0%</td><td style="color:#4ade80">+4.0%</td><td style="color:#4ade80">+7.0%</td><td style="color:#4ade80">+7.1%</td></tr>
  <tr><td style="color:#f87171">&#8593; 空头背离&#8805;4</td><td>19</td><td>0.5%</td><td style="color:#4ade80">+2.3%</td><td style="color:#4ade80">+5.1%</td><td style="color:#4ade80">+5.8%</td><td style="color:#4ade80">+9.1%</td><td style="color:#4ade80">+10.3%</td></tr>
</table>

<div class="box warn">
  <b>⚠️ 叠加背离的陷阱：</b>三重以上背离方向确定性强（60d=+7.1%），但N极小（仅70次占1.8%）。
  且均值靠少数暴涨拉升，中位数远低于均值。叠加位置过滤（+300下/BBlow）后中位数转负，说明大部分信号只是小涨小跌。
</div>

<h3>③ 位置过滤效果</h3>
<table>
  <tr><th>条件</th><th>N</th><th>20d均值</th><th>20d中位数</th><th>20d胜率</th><th>30d均值</th><th>45d均值</th></tr>
  <tr><td style="color:#facc15">背离&#8805;2 + BB低位</td><td>209</td><td style="color:#4ade80">+1.5%</td><td style="color:#4ade80">+0.5%</td><td>52%</td><td style="color:#4ade80">+2.2%</td><td style="color:#4ade80">+3.3%</td></tr>
  <tr><td style="color:#fb923c">背离&#8805;3 + BB低位</td><td>51</td><td style="color:#4ade80">+3.6%</td><td style="color:#4ade80">+1.5%</td><td>53%</td><td style="color:#4ade80">+3.5%</td><td style="color:#4ade80">+5.6%</td></tr>
  <tr><td style="color:#8b5cf6">OI>>vol alone</td><td>103</td><td style="color:#4ade80">+4.2%</td><td style="color:#4ade80">+3.7%</td><td>64%</td><td style="color:#4ade80">+5.4%</td><td style="color:#4ade80">+6.6%</td></tr>
</table>

<div class="box warn">
  <b>💡 背离信号的诚实诊断：</b><br><br>
  ● <b>是不是独立交易信号？</b> 大部分背离（HV涨+价跌、PCR涨+价跌、量涨+价跌）不够强——20d均值0.9-1.1%，胜率约50%，中位数接近零。<br><br>
  ● <b>哪些值得关注？</b><br>
  &nbsp;&nbsp;&#8226; <b>OI>>vol（机构背离）</b>N=103, 20d=+4.2%, 胜率64% ← 质量最高，信号最罕见<br>
  &nbsp;&nbsp;&#8226; <b>QVIX涨+价跌</b>N=142, 20d=+2.7%, 60d=+4.4%<br>
  &nbsp;&nbsp;&#8226; <b>三重以上叠加</b>N=70, 20d=+4.0%, 60d=+7.1%但中位数低<br><br>
  ● <b>背离最大的价值：</b>作为其他信号的确认器——当彩票策略/四象限信号触发且同时出现背离时，胜率提升。
  单独使用背离信号做交易，期望值不高。<br><br>
  ● <b>对比其他信号：</b>背离 vs 彩票（N=315, fwd20均值远超背离）vs QVIX策略（卖方夏普1.88），背离的信号质量排第三梯队。<br><br>
  ● <b>结论：</b>信号有，机会不大。适合辅助过滤，不适合独立交易。
</div>'''
    return h


def render_quadrant(data):
    """多空四象限框架 — 300均线 × 布林20轨道"""
    qp = os.path.join(DATA_DIR, "quadrant_framework.json")
    if not os.path.exists(qp):
        return '<div class="box warn">数据文件未生成，请先运行分析脚本。</div>'
    with open(qp) as f:
        q = json.load(f)
    
    quads = [
        ("long", "🟢", "顺势回调买call", "#4ade80"),
        ("short", "🔴", "逆势反弹买put", "#f87171"),
        ("lottery", "🎰", "超跌彩票买call", "#facc15"),
    ]
    
    h = '''
<div class="box info">
  <b>🎯 核心理念：</b>300均线定趋势（牛/熊），布林20轨道定入场时机。
  <br><br>
  ● <b>300上方</b> = 上升趋势 → 回调到下轨时<b>买call</b>（顺势）<br>
  ● <b>300下方</b> = 下降趋势 → 反弹到上轨时<b>买put</b>（逆势，效果弱）<br>
  ● <b>300下方+超跌</b> = 深度超跌 → <b>彩票买call</b><br>
</div>

<div class="box danger">
  <b>⚠️ 空头方向（300下+上轨买put）回测不成立。</b>创业板长期偏牛，
  空头信号胜率<50%，<b>请勿独立使用</b>。以下仅用作多空对称框架展示。
</div>

<h2>📊 四象限回测对比（20日持有）</h2>
<table>
  <tr><th>象限</th><th>操作</th><th>N</th><th>5d</th><th>胜率</th><th>10d</th><th>胜率</th><th>20d</th><th>胜率</th><th>>10%</th></tr>'''
    for qk, emoji, name, color in quads:
        if qk not in q["quadrants"]: continue
        qd = q["quadrants"][qk]
        h += f'<tr><td style="color:{color};font-weight:bold">{emoji} {name}</td>'
        h += f'<td style="color:{"#4ade80" if qk!="short" else "#f87171"}">{name}</td><td>{qd["n"]}</td>'
        for dk in ["5d","10d","20d"]:
            if dk in qd["holding"]:
                hd = qd["holding"][dk]
                c = "#4ade80" if hd["mean"]>0 else "#f87171"
                h += f'<td style="color:{c}">{hd["mean"]:+.1f}%</td><td>{hd["win_rate"]:.0f}%</td>'
            else:
                h += "<td>--</td><td>--</td>"
        h20 = qd["holding"].get("20d", {})
        h += f'<td>{h20.get("gt10_pct",0):.0f}%</td></tr>'
    h += '</table>'
    
    for qk, emoji, name, color in quads:
        if qk not in q["quadrants"]: continue
        qd = q["quadrants"][qk]
        h += f'<h2>{emoji} {name}（N={qd["n"]}）</h2><div class="kpi">'
        for dk in ["10d","20d","30d","45d"]:
            if dk in qd["holding"]:
                hd = qd["holding"][dk]
                c = "#4ade80" if hd["mean"]>0 else "#f87171"
                h += f'<div class="kpi-card"><div class="kpi-val" style="color:{c}">{hd["mean"]:+.1f}%</div><div class="kpi-label">{dk}均值</div></div>'
                h += f'<div class="kpi-card"><div class="kpi-val">{hd["win_rate"]:.0f}%</div><div class="kpi-label">{dk}胜率</div></div>'
                h += f'<div class="kpi-card warn"><div class="kpi-val">{hd["gt10_pct"]:.0f}%</div><div class="kpi-label">{dk}＆gt;10%</div></div>'
        h += '</div>'
        
        # HV分位
        if qd.get("hv_rets"):
            h += '<h3>🔮 波动率（HV_10）分位筛选</h3><table><tr><th>HV_10分位</th><th>N</th><th>fwd20</th></tr>'
            lab_map = {"hv_super_low":"HV极低<25%","hv_low":"HV低25-50%","hv_high":"HV高50-75%","hv_super_high":"HV极高>75%"}
            for lab, lab_name in lab_map.items():
                if lab in qd["hv_rets"]:
                    hd = qd["hv_rets"][lab]
                    c = "#4ade80" if hd["fwd20"]>0 else "#f87171"
                    h += f'<tr><td>{lab_name}</td><td>{hd["n"]}</td><td style="color:{c}">{hd["fwd20"]:+.1f}%</td></tr>'
            h += '</table>'
        
        # 最近信号
        h += '<h3>📅 最近信号</h3><table><tr><th>日期</th><th>收盘</th><th>20d涨</th><th>量比</th><th>fwd20</th></tr>'
        for sig in qd.get("recent_signals", [])[::-1][-10:]:
            f20 = f'{sig["fwd20"]:+.0f}%' if sig.get("fwd20") is not None else '--'
            c20 = "#4ade80" if (sig.get("fwd20") or 0) > 0 else "#f87171" if (sig.get("fwd20") or 0) < 0 else "#94a3b8"
            h += f'<tr><td>{sig["date"]}</td><td>{sig["close"]:.0f}</td><td>{sig["ret_20d"]:+.0f}%</td><td>{sig["vol_ratio"]:.1f}x</td><td style="color:{c20}">{f20}</td></tr>'
        h += '</table>'
    
    h += '''
<h2>💡 波动率升维：期权结构选择</h2>
<div class="box success">
  <b>基于回测的期权选结构建议：</b><br><br>
  ● <b>HV极低（<25%分位）</b> → 买<b>虚值call</b>，持有30天（波动小+期权便宜）<br>
  ● <b>HV低-中（25-50%分位）</b> → 买<b>平值call</b>，持有20天<br>
  ● <b>HV高（50-75%分位）</b> → 买<b>平值/实值call</b>，持有15天<br>
  ● <b>HV极高（>75%分位）</b> → 买<b>实值call</b>，持有10天（快进快出）<br><br>
  <b>原理：</b>HV低时虚值期权成本低、杠杆高，赌反弹性价比最好；
  HV高时实值call时间价值损耗少，适合顺势跟。<br><br>
  <b>⏱️ 持有期：</b>30天各象限综合最均衡（胜率62-72%）。5-10天太短，45天时间价值大。<br><br>
  <b>当前（2026-05-15）：</b>等待信号触发中...
</div>'''
    return h



SIGNALS = [
    {"slug":"granger", "title":"量价因果：成交量→波动率 Granger", "emoji":"&#128279;",
     "desc":"统计检验成交量是否包含预测波动率的信息。", "fn": render_granger},
    {"slug":"garchx",  "title":"GARCH-X：成交量对条件波动率的解释力", "emoji":"&#128202;",
     "desc":"GARCH(1,1)框架下成交量作为外生变量的拟合优度。", "fn": render_garchx},
    {"slug":"pcr",     "title":"PCR 期权情绪：认沽认购比", "emoji":"&#128201;",
     "desc":"期权市场的多空分歧信号。", "fn": render_pcr},
    {"slug":"qvix",    "title":"QVIX：隐含波动率", "emoji":"&#127777;",
     "desc":"期权市场对未来30天波动率的集体预期。不能判断方向。", "fn": render_qvix},
    {"slug":"vol_ratio","title":"vol_ratio：短期 vs 长期波动率比", "emoji":"&#128200;",
     "desc":"5日RV/60日RV，衡量波动率是否在加速/衰减。", "fn": render_vol_ratio},
    {"slug":"dual_signal","title":"双重信号：QVIX + vol_ratio", "emoji":"&#128308;",
     "desc":"两个维度同时预警时，波动率飙升确定性最高。", "fn": render_dual},
    {"slug":"qvix_strategy","title":"QVIX 波动率套利策略", "emoji":"&#128176;",
     "desc":"基于QVIX历史分位的期权买卖信号（买方/卖方双向）。", "fn": render_qvix_strategy},
    {"slug":"lottery","title":"末日彩票：超跌末日期权策略", "emoji":"&#127922;",
     "desc":"布林下轨+超跌时买入6天末日call，正期望期权策略。", "fn": render_lottery},
    {"slug":"thermometer","title":"市场温度计：全状态分类系统", "emoji":"&#127777;&#65039;",
     "desc":"平静/躁动/异动/预备爆发/风暴 —— 基于成交量×波动率的市场状态分类。", "fn": render_thermometer},
    {"slug":"eruption","title":"爆发事件诚实分类：我们预测不了什么", "emoji":"&#9968;&#65039;",
     "desc":"不是过拟合——我们诚实标注了哪些爆发可以预测，哪些不能。", "fn": render_eruption_honesty},
    {"slug":"divergence","title":"背离信号：价格&波动率恐慌背离", "emoji":"&#9888;&#65039;",
     "desc":"多维度恐慌背离/机构背离检测（HV/QVIX/PCR/OI）。", "fn": render_divergence},
    {"slug":"quadrant","title":"多空四象限：300均线×布林轨道", "emoji":"&#128260;",
     "desc":"300均线上方+布林下轨买call，300下方+超跌买彩票。", "fn": render_quadrant},
]

def dashboard(signals, data):
    q = data.get("qvix_analysis", {})
    p = data.get("pcr_analysis", {}).get("basic_stats", {})

    alerts = []
    lq = q.get("latest_qvix", 0)
    if lq > 35:
        alerts.append(f"QVIX={lq:.0f}(>35) — 隐含波动率偏高，仓位管理建议关注")
    pc = p.get("vol_pcr_current", 0)
    if pc < 0.7:
        alerts.append(f"PCR(量)={pc:.2f}(<0.7) — 期权市场极度乐观")
    elif pc > 1.2:
        alerts.append(f"PCR(量)={pc:.2f}(>1.2) — 期权市场恐慌对冲")

    cards = ''
    for s in signals:
        cards += f'''
        <a href="signals/{s['slug']}.html" class="signal-card">
          <div class="signal-emoji">{s['emoji']}</div>
          <div class="signal-title">{s['title']}</div>
          <div class="signal-desc">{s['desc'][:80]}{'...' if len(s['desc'])>80 else ''}</div>
        </a>'''

    alert_html = ''
    if alerts:
        alert_html = f'<div class="box danger"><h3 style="margin-bottom:8px;">当前活跃预警</h3><ul>{"".join(f"<li>{a}</li>" for a in alerts)}</ul></div>'

    full = BT["strategy"]["full"]
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CYB MDH 信号仪表盘</title>
<style>
{CSS}
.signal-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:15px; margin:20px 0; }}
.signal-card {{ background:#1e293b; border-radius:12px; padding:18px; text-decoration:none; color:#e2e8f0; display:block; transition:transform 0.15s,box-shadow 0.15s; border:1px solid #334155; }}
.signal-card:hover {{ transform:translateY(-2px); box-shadow:0 4px 15px rgba(96,165,250,0.15); border-color:#60a5fa; }}
.signal-emoji {{ font-size:2em; margin-bottom:6px; }}
.signal-title {{ font-size:1em; font-weight:bold; color:#60a5fa; margin-bottom:4px; }}
.signal-desc {{ font-size:0.82em; color:#94a3b8; }}
.qt {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin:20px 0; }}
.qtc {{ background:#1e293b; border-radius:10px; padding:15px; text-align:center; border-left:3px solid; }}
.qtv {{ font-size:1.4em; font-weight:bold; }}
.qtl {{ font-size:0.8em; color:#94a3b8; }}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>&#129428; 创业板(159915) 信号仪表盘</h1>
  <p class="subtitle">基于全周期回测(2010-2026) &middot; 所有结论基于真实数据</p>
</header>

{alert_html}

<div class="qt">
  <div class="qtc" style="border-color:#4ade80">
    <div class="qtv" style="color:#60a5fa">{len(signals)}</div>
    <div class="qtl">总信号数</div>
  </div>
  <div class="qtc" style="border-color:#4ade80">
    <div class="qtv" style="color:#facc15">{full["ann"]:.0f}%</div>
    <div class="qtl">满仓基准年化(2010起)</div>
  </div>
  <div class="qtc" style="border-color:#f87171">
    <div class="qtv" style="color:#f87171">{full["dd"]:.0f}%</div>
    <div class="qtl">满仓最大回撤</div>
  </div>
  <div class="qtc" style="border-color:#4ade80">
    <div class="qtv" style="color:#facc15">{q.get("latest_qvix",0):.0f} ({q.get("latest_percentile",0):.0f}%)</div>
    <div class="qtl">当前QVIX(分位)</div>
  </div>
</div>

<h2>&#128225; 信号列表</h2>
<div class="signal-grid">{cards}</div>

<div class="box warn">
  <b>&#9888; 诚实说明：</b>所有简单波动率减仓策略均跑输满仓持有。
  高量/高波区间恰好是创业板涨幅最大的时期。<br>
  这些信号用于<u>波动率估计和风险感知</u>，不是仓位调节信号。
</div>

<footer>
  CYB MDH Analysis &middot;
  <a href="https://github.com/whao79-sudo/cyb-mdh-analysis" style="color:#60a5fa;">GitHub</a> &middot;
  <a href="output/cyb_mdh_analysis.html" style="color:#60a5fa;">完整图表</a> &middot;
  <a href="output/pcr_analysis.html" style="color:#60a5fa;">PCR图</a> &middot;
  <a href="output/qvix_signal_chart.html" style="color:#60a5fa;">QVIX信号图</a>
</footer>
</div>
</body>
</html>'''

def main():
    json_path = os.path.join(DATA_DIR, "mdh_report.json")
    with open(json_path) as f:
        data = json.load(f)
    os.makedirs(SIGNALS_DIR, exist_ok=True)

    for s in SIGNALS:
        content = s["fn"](data)
        html = page_html(s["title"], s["emoji"], s["desc"], content)
        path = os.path.join(SIGNALS_DIR, f"{s['slug']}.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  {s['emoji']} {path}")

    idx = dashboard(SIGNALS, data)
    ipath = os.path.join(DOCS_DIR, "index.html")
    with open(ipath, 'w', encoding='utf-8') as f:
        f.write(idx)
    print(f"\n仪表盘: {ipath}")

if __name__ == "__main__":
    main()
