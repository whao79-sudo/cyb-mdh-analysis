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
    # 加载策略回测数据
    sp = os.path.join(DATA_DIR, "qvix_strategy.json")
    if not os.path.exists(sp):
        return "<div class='box warn'><b>策略数据尚未生成。</b>运行 fetch_qvix.py 和回测脚本可生成。</div>"
    with open(sp) as f:
        s = json.load(f)

    h = ''
    # 当前信号
    cur = s["current_signal"]
    now_q = s["latest_qvix"]
    now_pct = s["qvix_pct_60"]
    sig_emoji = "💰" if cur == "卖出期权(卖方)" else "🔥" if cur == "买入期权" else "⏸️"
    sig_color = "warn" if cur == "无信号" else "success"
    h += '<div class="kpi">'
    h += card(f"{now_q:.1f}%", f"QVIX ({s['latest_date']})", "warn" if now_q > 30 else "good")
    h += card(f"{now_pct:.0f}%", "60日分位", "bad" if now_pct > 80 else "good")
    h += card(f"{sig_emoji} {cur}", "当前策略信号", sig_color, fmt="s")
    h += '</div>'

    # 策略说明
    h += f'''<div class="box info">
      <b>策略逻辑：</b>QVIX处于15-30%历史分位 → IV偏低 → 买入期权（赌波动率回升）。<br>
      QVIX处于40-60%历史分位 → IV偏高 → 卖出期权（卖方，赚波动率溢价回归）。<br>
      当前QVIX={now_q:.0f}%处于60日{now_pct:.0f}%分位，{cur}。
    </div>'''

    bbt = s["buy_backtest"]
    sbt = s["sell_backtest"]
    h += '<h2>回测结果 (2022-09 ~ 至今)</h2>'
    h += '<table><tr><th>策略</th><th>信号数</th><th>10日后ΔQVIX</th><th>期权估算收益</th><th>胜率</th></tr>'
    h += f'<tr><td>买方 (IV 15-30%分位)</td><td>{bbt["total"]}</td><td>{bbt["avg_delta_qvix_10d"]:+.1f}pp</td><td style="color:#4ade80">{bbt["avg_opt_ret_10d"]:+.1f}%</td><td>{bbt["win_rate"]}%</td></tr>'
    h += f'<tr><td>卖方 (IV 40-60%分位)</td><td>{sbt["total"]}</td><td>{sbt["avg_delta_qvix_10d"]:+.1f}pp</td><td style="color:#f87171">{sbt["avg_opt_ret_10d"]:+.1f}%</td><td>{sbt["win_rate"]}%</td></tr>'
    h += '</table>'

    # 最近信号
    h += '<h3>最近几次买入信号详情</h3>'
    h += '<table><tr><th>日期</th><th>QVIX</th><th>分位</th><th>10日后ΔQVIX</th><th>期权收益</th></tr>'
    for r in s["recent_buy_signals"][-5:]:
        dq = r.get("fwd_delta_qvix", "--")
        op = r.get("opt_ret", "--")
        if dq is None: dq = "--"
        if op is None: op = "--"
        col = "color:#4ade80" if (isinstance(op, (int,float)) and op > 0) else "color:#f87171" if (isinstance(op, (int,float)) and op < 0) else ""
        h += f'<tr><td>{r["date"]}</td><td>{r["qvix"]}%</td><td>{r["pct"]}%</td><td>{dq}</td><td style="{col}">{op}</td></tr>'
    h += '</table>'

    h += f'''<div class="box warn">
      <b>⚠️ 局限：</b>期权收益基于简化模型（vega=5x），未计交易成本。QVIX数据仅2022年9月起（874个交易日），
      策略样本量有限。N(买方)={bbt["total"]}次，N(卖方)={sbt["total"]}次。
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
