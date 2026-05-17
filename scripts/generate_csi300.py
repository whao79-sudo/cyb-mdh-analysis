#!/usr/bin/env python3
"""沪深300(000300) 策略回测信号页面"""
import pandas as pd, numpy as np, baostock as bs, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIG_DIR = os.path.join(BASE, 'docs', 'csi300')

def card(val, label, cls="normal"):
    c = {"good":"#4ade80","bad":"#f87171","warn":"#facc15","normal":"#60a5fa"}.get(cls, "#94a3b8")
    return f'<div class="kpi-card" style="border-color:{c}"><div class="kpi-val" style="color:{c}">{val}</div><div class="kpi-label">{label}</div></div>'

def load_data():
    bs.login()
    rs = bs.query_history_k_data_plus('sh.000300', 'date,close',
        start_date='2010-01-01', end_date='2026-05-17',
        frequency='d', adjustflag='3')
    data = [[d[0], float(d[1])] for d in rs.data]
    bs.logout()
    df = pd.DataFrame(data, columns=['date','close'])
    df['date'] = pd.to_datetime(df['date']); df = df.set_index('date').sort_index()
    df['ret'] = df['close'].pct_change() * 100
    df['vol_10'] = df['ret'].rolling(10).std() * np.sqrt(252)
    df['vol_22'] = df['ret'].rolling(22).std() * np.sqrt(252)
    df['ma300'] = df['close'].rolling(300).mean()
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lo'] = df['bb_mid'] - 2*df['bb_std']
    df['bb_pos'] = (df['close'] - df['bb_lo']) / (4*df['bb_std']) * 100
    for d in [3,5,6,8,10,15,20,22,30]:
        df[f'fwd{d}_ret'] = df['close'].pct_change(d).shift(-d) * 100
    df['vol_rank'] = df['vol_22'].rolling(504).apply(
        lambda x: pd.Series(x.dropna()).rank(pct=True).iloc[-1]*100 if len(x.dropna())>0 else 50, raw=False)
    df['drop20'] = df['close'] / df['close'].shift(20) - 1
    return df

def page_csi300():
    df = load_data().dropna(subset=['vol_22','ma300','vol_rank'])
    cur = df.index[-1]; cur_r = df.loc[cur]
    hv = cur_r['vol_22']; bbp = cur_r['bb_pos']; ab300 = cur_r['close']>cur_r['ma300']
    drink = (cur_r['close']/df['close'].shift(20).loc[cur]-1)*100; vr = cur_r['vol_rank']
    h = f'''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>沪深300(000300) 期权策略参考</title>
<link rel="stylesheet" href="../style.css"></head><body>
<header><h1>&#127185; 沪深300(000300) 期权策略参考</h1>
<p class="subtitle">深交所300ETF(510300/159919) 标底指数 &middot; 2012-2026回测</p></header>

<div class="kpi">
  {card(f'{hv:.1f}%','当前HV22')}
  {card(f'{bbp:.0f}%','布林位置')}
  {card(f'{"&#128200;上" if ab300 else "&#128200;下"}','300均线')}
  {card(f'{drink:+.1f}%','20日涨跌')}
  {card(f'{vr:.0f}%分位','vol_rank')}
</div>

<div class="box info">
  <b>&#127185; 沪深300 vs 创业板 核心差异</b><br>
  &#8226; HV均值19.0% — 三个指数中最稳定，波动最小<br>
  &#8226; 彩票N=73（2.1%时间），介于创业板(35)和中证500(505)之间<br>
  &#8226; <b style="color:#f87171">恐慌暴跌反弹效应极弱</b> — 300下恐慌20d仅+0.53%（中证500=+3.23%）<br>
  &#8226; <b style="color:#f87171">恐慌反弹(300上)全部负收益</b> — 别在300上方恐慌时买call<br>
  &#8226; 高波(vol>30)区间整体负收益 — 沪深300高波是卖出信号<br>
  &#8226; <b>机构化程度最高</b> — 波动率曲面定价效率高，期权套利空间小
</div>

<h2>&#127922; 彩票超跌（布林<15 + 20d跌>8%）, N=73</h2>
<table><tr><th>条件</th><th>N</th><th>5d</th><th>5dW</th><th>10d</th><th>20d</th><th>20dW</th><th>30d</th><th>30dW</th><th>>10%</th></tr>'''

    for name, cond in [
        ("彩票(全)", (df['bb_pos']<=15)&(df['drop20']<-0.08)),
        ("彩票+低波(v<20)", (df['bb_pos']<=15)&(df['drop20']<-0.08)&(df['vol_10']<20)),
        ("彩票+高波(v>=30)", (df['bb_pos']<=15)&(df['drop20']<-0.08)&(df['vol_10']>=30)),
    ]:
        s = df[cond].dropna(subset=['fwd20_ret']); n = len(s)
        if n<3: continue
        h += f'<tr><td>{name}</td><td>{n}</td>'
        for d in [5,10,20,30]:
            ss = df[cond].dropna(subset=[f'fwd{d}_ret']); n2 = len(ss)
            if n2<3: h += '<td>--</td>'; continue
            raw = ss[f'fwd{d}_ret']; m = raw.mean(); wr = (raw>0).mean()*100; c = '#4ade80' if m>0 else '#f87171'
            if d==20: gt10 = (raw>10).mean()*100; h += f'<td style="color:{c}">{m:+.1f}%<br><small style="color:#94a3b8">W{wr:.0f}%</small></td>'
            elif d==30: gt10_30 = (raw>10).mean()*100; h += f'<td style="color:{c}">{m:+.1f}%</td><td>{wr}%</td><td>{gt10_30:.0f}%</td>'
            else: h += f'<td style="color:{c}">{m:+.1f}%</td>'; h += f'<td>{wr}%</td>' if d==5 else ''
        h += '</tr>'

    h += '''</table>

<div class="box warn">
  <b>&#127922; 沪深300彩票的特殊性</b><br>
  &#8226; N=73偏小，但比创业板(35)大了一倍<br>
  &#8226; 最佳到期日：<b>6-15天</b>（6d=+1.20%胜率71%，15d=+1.86%胜率70%）<br>
  &#8226; 与中证500的"20-30d"不同——沪深300反弹节奏更快（因机构资金涌入）<br>
  &#8226; 高波(v>=30)时彩票N=43但20d=-0.33%——高波区彩票无效<br>
  &#8226; 行权价建议：<b>平值-5%</b>（P90收益小，>10%概率仅3-15%）
</div>

<h2>&#128163; 恐慌模式</h2>
<table><tr><th>条件</th><th>N</th><th>3d</th><th>5d</th><th>10d</th><th>20d</th><th>20dW</th><th>30d</th></tr>'''

    for name, cond in [
        ("恐慌暴跌(vol>90+300下)", (df['vol_rank']>=90)&(df['close']<df['ma300'])),
        ("恐慌反弹(vol>90+300上)", (df['vol_rank']>=90)&(df['close']>df['ma300'])),
    ]:
        s = df[cond].dropna(subset=['fwd20_ret']); n = len(s)
        if n<3: continue
        h += f'<tr><td>{name}</td><td>{n}</td>'
        for d in [3,5,10,20,30]:
            ss = df[cond].dropna(subset=[f'fwd{d}_ret']); n2 = len(ss)
            if n2<3: h += '<td>--</td>'; continue
            raw = ss[f'fwd{d}_ret']; m = raw.mean(); c = '#4ade80' if m>0 else '#f87171'
            if d==20: wr = (raw>0).mean()*100; h += f'<td style="color:{c}">{m:+.1f}%<br><small>W{wr:.0f}%</small></td>'
            else: h += f'<td style="color:{c}">{m:+.1f}%</td>'
        h += '</tr>'
    h += '''</table>

<div class="box warn">
  <b>&#128163; 沪深300恐慌：三个品种中最差</b><br>
  &#8226; 恐慌暴跌(300下) N=192: 20d=+0.53%胜率55% — 基本没反弹<br>
  &#8226; 恐慌反弹(300上) N=291: <b style="color:#f87171">所有到期日全部负收益</b> — 30d=-2.66%<br>
  &#8226; <b>结论：</b>沪深300不需要恐慌抄底策略。高波本身就是卖出信号。
</div>

<h2>&#128200; 趋势策略</h2>
<table><tr><th>模式</th><th>N</th><th>3d</th><th>5d</th><th>10d</th><th>20d</th><th>30d</th></tr>'''

    for name, cond, color in [
        ("高波+300下(反弹)", (df['vol_10']>=30)&(df['close']<df['ma300']), '#fb923c'),
        ("高波+300上(负)别碰", (df['vol_10']>=30)&(df['close']>df['ma300']), '#f87171'),
        ("低波+300上(慢牛)", (df['vol_10']<20)&(df['close']>df['ma300']), '#4ade80'),
        ("低波+300下(观望)", (df['vol_10']<20)&(df['close']<df['ma300']), '#94a3b8'),
    ]:
        s = df[cond].dropna(subset=['fwd30_ret']); n = len(s)
        if n<3: continue
        h += f'<tr style="color:{color}"><td>{name}</td><td>{n}</td>'
        for d in [3,5,10,20,30]:
            ss = df[cond].dropna(subset=[f'fwd{d}_ret'])
            if len(ss)<3: h += '<td>--</td>'; continue
            m = ss[f'fwd{d}_ret'].mean(); c = '#4ade80' if m>0 else '#f87171'
            h += f'<td style="color:{c}">{m:+.1f}%</td>'
        h += '</tr>'

    h += '''</table>

<div class="box good">
  <b>&#128200; 沪深300唯一可靠的策略</b><br>
  &#8226; <b>高波+300下(N=154)：</b>20d=+2.04%胜率70%，30d=+3.71%胜率75%←<b style="color:#4ade80">最佳信号</b><br>
  &#8226; <b>低波+300上(N=1245,36%时间)：</b>20d=+1.33%胜率60%←主策略<br>
  &#8226; <span style="color:#f87171">高波+300上(别碰)：</span>所有到期日负收益，30d=-3.33%<br>
  &#8226; <span style="color:#94a3b8">低波+300下(观望)：</span>N=1207(35%时间)但收益几乎为0，别买
</div>

<h2>&#128197; 到期日选择指南（沪深300）</h2>
<table>
  <tr><th>模式</th><th>最佳到期日</th><th>均值</th><th>胜率</th><th>行权价</th><th>优先级</th></tr>
  <tr><td>&#127922; 彩票</td><td>6-15d</td><td>+1.2~1.9%</td><td>64-71%</td><td>平值-5%</td><td>N=73可用</td></tr>
  <tr><td>&#128200; 高波+300下</td><td>15-30d</td><td>+2.0~3.7%</td><td>70-75%</td><td>平值-5%</td><td>&#9733;最佳</td></tr>
  <tr><td>&#128200; 低波+300上</td><td>22-30d</td><td>+1.3~2.1%</td><td>60-61%</td><td>平值</td><td>主策略</td></tr>
  <tr><td>&#128163; 恐慌暴跌(300下)</td><td>不用</td><td>+0.5%</td><td>~55%</td><td>—</td><td>不值得</td></tr>
  <tr><td>&#128163; 恐慌反弹(300上)</td><td>不买</td><td>-</td><td>-</td><td>—</td><td>全负</td></tr>
  <tr><td>&#128683; 低波+300下</td><td>观望</td><td>~0%</td><td>42-45%</td><td>不适合</td><td>不做</td></tr>
</table>

<div class="box">
  <b>&#128276; 策略总结</b><br>
  &#8226; <b>沪深300不适合彩票策略</b> — 反弹慢、胜率低、>10%概率极小<br>
  &#8226; <b>恐慌信号在这里是反向指标</b> — 300上方恐慌20d=-2.05%<br>
  &#8226; <b>唯一赚钱策略：趋势</b> — 低波+300上慢牛(36%时间) 或 高波+300下反弹<br>
  &#8226; <b>当前（{cur.date()}）：</b>HV={hv:.1f}%，300{"上方" if ab300 else "下方"}，布林{bbp:.0f}%，20日{drink:+.1f}%
</div>

<footer><p>数据源：baostock &#8226; 回测：2012-2026</p></footer>
</body></html>'''
    os.makedirs(SIG_DIR, exist_ok=True)
    with open(os.path.join(SIG_DIR, 'index.html'), 'w') as f: f.write(h)
    print(f"  CSI300: {os.path.join(SIG_DIR, 'index.html')}")

if __name__ == '__main__':
    page_csi300()
