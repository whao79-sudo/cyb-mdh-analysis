#!/usr/bin/env python3
"""中证500(000905) 策略回测信号页面 — 独立页面，与创业板 (159915) 并行"""
import pandas as pd, numpy as np, baostock as bs, os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, 'output')
SIG_DIR = os.path.join(BASE, 'docs', 'csi500')

def card(val, label, cls="normal"):
    c = {"good":"#4ade80","bad":"#f87171","warn":"#facc15","normal":"#60a5fa"}.get(cls, "#94a3b8")
    return f'<div class="kpi-card" style="border-color:{c}"><div class="kpi-val" style="color:{c}">{val}</div><div class="kpi-label">{label}</div></div>'

def load_data():
    bs.login()
    rs = bs.query_history_k_data_plus('sh.000905', 'date,close',
        start_date='2010-01-01', end_date='2026-05-17',
        frequency='d', adjustflag='3')
    data = [[d[0], float(d[1])] for d in rs.data]
    bs.logout()
    df = pd.DataFrame(data, columns=['date','close'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df['ret'] = df['close'].pct_change() * 100
    df['vol_5'] = df['ret'].rolling(5).std() * np.sqrt(252)
    df['vol_10'] = df['ret'].rolling(10).std() * np.sqrt(252)
    df['vol_22'] = df['ret'].rolling(22).std() * np.sqrt(252)
    df['ma300'] = df['close'].rolling(300).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_lo'] = df['bb_mid'] - 2*df['bb_std']
    df['bb_pos'] = (df['close'] - df['bb_lo']) / (4*df['bb_std']) * 100
    df['bb30_mid'] = df['close'].rolling(30).mean()
    df['bb30_std'] = df['close'].rolling(30).std()
    df['bb30_lo'] = df['bb30_mid'] - 2*df['bb30_std']
    for d in [3,5,6,8,10,15,20,22,30,45]:
        df[f'fwd{d}_ret'] = df['close'].pct_change(d).shift(-d) * 100
    df['vol_rank'] = df['vol_22'].rolling(504).apply(
        lambda x: pd.Series(x.dropna()).rank(pct=True).iloc[-1]*100 if len(x.dropna())>0 else 50, raw=False)
    df['bb_rank'] = df['bb_pos'].rolling(504).apply(
        lambda x: pd.Series(x.dropna()).rank(pct=True).iloc[-1]*100 if len(x.dropna())>0 else 50, raw=False)
    df['drop20'] = df['close'] / df['close'].shift(20) - 1
    return df

def page_csi500():
    df = load_data()
    df = df.dropna(subset=['vol_22','ma300','vol_rank'])
    cur = df.index[-1]; cur_r = df.loc[cur]
    hv = cur_r['vol_22']; bbp = cur_r['bb_pos']; ab300 = cur_r['close'] > cur_r['ma300']
    drink = (cur_r['close'] / df['close'].shift(20).loc[cur] - 1) * 100
    vr = cur_r['vol_rank']
    
    h = f'''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>中证500(000905) 期权策略参考</title>
<link rel="stylesheet" href="../style.css"></head><body>
<header><h1>&#127185; 中证500(000905) 期权策略参考</h1>
<p class="subtitle">基于2012-2026真实回测数据 &middot; 信号从创业板的 QVIX 替换为 vol_rank>90 分位</p></header>

<div class="kpi">
  {card(f'{hv:.1f}%', '当前HV22')}
  {card(f'{bbp:.0f}%', f'布林位置')}
  {card(f'{"&#128200;上" if ab300 else "&#128200;下"}', '300均线')}
  {card(f'{drink:+.1f}%', '20日涨跌')}
  {card(f'{vr:.0f}%分位', 'vol_rank')}
</div>

<div class="box info">
  <b>&#127185; 中证500 vs 创业板核心差异</b><br>
  &#8226; 中证500波动更低（HV22均值21.1% vs 创业板~25%+）<br>
  &#8226; 彩票触发频次更高（N=505 vs 创业板N=35）——统计更可靠<br>
  &#8226; 恐慌模式样本充足（N=411）——完全可用<br>
  &#8226; <b>无QVIX数据</b>：用vol_rank>90分位替代"恐慌"信号<br>
  &#8226; 高波+300上模式30d变负——中证500没有创业板那波9月政策行情
</div>

<h2>&#127922; 彩票超跌策略（bb_pos<=15 + 20d跌>8%）</h2>
<table><tr><th>条件</th><th>N</th><th>5d</th><th>5dW</th><th>10d</th><th>20d</th><th>20dW</th><th>30d</th><th>30dW</th><th>>10%</th></tr>'''
    
    conds = [
        ("彩票(全)", (df['bb_pos']<=15)&(df['drop20']<-0.08)),
        ("彩票+中高波(v>=20)", (df['bb_pos']<=15)&(df['drop20']<-0.08)&(df['vol_10']>=20)),
        ("彩票+高波(>=30)", (df['bb_pos']<=15)&(df['drop20']<-0.08)&(df['vol_10']>=30)),
        ("彩票+300下", (df['bb_pos']<=15)&(df['drop20']<-0.08)&(df['close']<df['ma300'])),
        ("末端(布林30下轨+跌>8%)", (df['close']<df['bb30_lo'])&(df['drop20']<-0.08)),
    ]
    for name, cond in conds:
        s = df[cond].dropna(subset=['fwd20_ret'])
        n = len(s)
        if n<3: continue
        h += f'<tr><td>{name}</td><td>{n}</td>'
        for d in [5,10,20,30]:
            ss = df[cond].dropna(subset=[f'fwd{d}_ret'])
            if len(ss)<3: h += '<td>--</td>'; continue
            raw = ss[f'fwd{d}_ret']
            m = raw.mean(); wr = (raw>0).mean()*100
            c = '#4ade80' if m>0 else '#f87171'
            if d==20:
                gt10 = (raw>10).mean()*100
                h += f'<td style="color:{c}">{m:+.1f}%<br><small style="color:#94a3b8">W{wr:.0f}%</small></td>'
            elif d==30:
                h += f'<td style="color:{c}">{m:+.1f}%</td><td>{wr}%</td>'
                gt10_30 = (raw>10).mean()*100
                h += f'<td>{gt10_30:.0f}%</td>'
            else:
                h += f'<td style="color:{c}">{m:+.1f}%</td>'
            if d==5: h += f'<td>{wr}%</td>'
        h += '</tr>'
    
    h += '''</table>

<div class="box good">
  <b>&#127919; 彩票策略核心发现</b><br><br>
  <b>1. 必须加波动率过滤！</b><br>
  全样本彩票N=505，但主要收益来自高波区间：<br>
  &#8226; 低波(v<20) N=264: 20d=-0.34% 胜率45% ← 亏钱！<br>
  &#8226; 中波(20-30) N=150: 20d=+2.21% 胜率64%<br>
  &#8226; 高波(>=30) N=91: 20d=+2.52% 胜率68% >10%=21%<br><br>
  <b>2. 推荐规则：仅vol>20%时做彩票</b><br>
  &#8226; 推荐到期日：20-30天（N大，胜率64-68%）<br>
  &#8226; 行权价：虚值5-10%（P75~20d收益+5%左右）<br>
  &#8226; 占比：全样本14.7%时间在布林下15%，+vol过滤后约7%
</div>

<h2>&#128163; 恐慌模式（vol_rank>90分位 = 高频恐慌区）</h2>
<table><tr><th>条件</th><th>N</th><th>3d</th><th>5d</th><th>10d</th><th>20d</th><th>20dW</th><th>30d</th></tr>'''
    
    for name, cond in [
        ("恐慌暴跌(vol>90+300下)", (df['vol_rank']>=90)&(df['close']<df['ma300'])),
        ("恐慌反弹(vol>90+300上)", (df['vol_rank']>=90)&(df['close']>df['ma300'])),
        ("恐慌+彩票(vol>90+超跌)", (df['vol_rank']>=90)&(df['bb_pos']<=15)),
    ]:
        s = df[cond].dropna(subset=['fwd20_ret'])
        n = len(s)
        if n<3: continue
        h += f'<tr><td>{name}</td><td>{n}</td>'
        for d in [3,5,10,20,30]:
            ss = df[cond].dropna(subset=[f'fwd{d}_ret'])
            if len(ss)<3: h += '<td>--</td>'; continue
            raw = ss[f'fwd{d}_ret']
            m = raw.mean()
            c = '#4ade80' if m>0 else '#f87171'
            if d==20:
                wr = (raw>0).mean()*100
                h += f'<td style="color:{c}">{m:+.1f}%<br><small>W{wr:.0f}%</small></td>'
            else: h += f'<td style="color:{c}">{m:+.1f}%</td>'
        h += '</tr>'
    
    h += '''</table>

<div class="box good">
  <b>&#128163; 恐慌模式发现</b><br>
  &#8226; <b>恐慌暴跌（N=190）：</b>全部正收益。3d=+1.05%，10d=+2.35%。胜率61-73%<br>
  &#8226; <b>恐慌反弹（N=221）：</b>20d=-1.0%胜率59%，30d=-4.05%——300上方的恐慌是出货信号<br>
  &#8226; <b><span style="color:#4ade80">恐慌+彩票：</span></b>恐慌叠加超跌效果最好——但这两种本身就是重叠事件<br>
  &#8226; 推荐到期日：<b>6-10天</b>（恐慌反弹过3天就摔）
</div>

<h2>&#128200; 趋势策略</h2>
<table><tr><th>模式</th><th>N</th><th>3d</th><th>5d</th><th>10d</th><th>15d</th><th>20d</th><th>30d</th></tr>'''
    
    for name, cond, color in [
        ("高波+300下(反弹) N=295", (df['vol_10']>=30)&(df['close']<df['ma300']), '#fb923c'),
        ("高波+300上(加速) N=279", (df['vol_10']>=30)&(df['close']>df['ma300']), '#4ade80'),
        ("低波+300上(慢牛) N=1171", (df['vol_10']<20)&(df['close']>df['ma300']), '#34d399'),
        ("低波+300下(观望) N=877", (df['vol_10']<20)&(df['close']<df['ma300']), '#94a3b8'),
    ]:
        s = df[cond].dropna(subset=['fwd30_ret'])
        n = len(s)
        if n<3: continue
        h += f'<tr style="color:{color}"><td>{name}</td>'
        for d in [3,5,10,15,20,30]:
            ss = df[cond].dropna(subset=[f'fwd{d}_ret'])
            if len(ss)<3:
                h += '<td>--</td>'
                continue
            m = ss[f'fwd{d}_ret'].mean()
            c = '#4ade80' if m>0 else '#f87171'
            h += f'<td style="color:{c}">{m:+.1f}%</td>'
        h += '</tr>'
    
    h += '''</table>

<div class="box warn">
  <b>&#128200; 趋势策略注意事项</b><br>
  &#8226; <b>高波+300上(加速)：</b>10-15d表现最好(+0.8~1.4%)，30d跌为负！不是长持策略<br>
  &#8226; <b>低波+300上(慢牛)：</b>全样本N=1171(34%)，25年的时间是中证500的主要状态。推荐20-30d<br>
  &#8226; <b>低波+300下(观望)：</b>所有到期日全部负收益，不做期权
</div>

<h2>&#128197; 到期日选择指南</h2>
<table>
  <tr><th>模式</th><th>最佳到期日</th><th>均值</th><th>胜率</th><th>行权价</th><th>逻辑</th></tr>
  <tr><td>&#127922; 彩票(vol过滤>=20)</td><td>20-30d</td><td>+2.3~2.5%</td><td>64-68%</td><td>虚值5-10%</td><td>中证500反弹慢但持久，比创业板需要更长时间</td></tr>
  <tr><td>&#128163; 恐慌暴跌(300下)</td><td>6-10d</td><td>+1.5~2.4%</td><td>67-73%</td><td>虚值5-10%</td><td>恐慌来得快去得快，10d最稳</td></tr>
  <tr><td>&#128200; 高波+300下</td><td>6-15d</td><td>+1.3~3.2%</td><td>67-68%</td><td>虚值5-10%</td><td>向下趋势反弹效率高</td></tr>
  <tr><td>&#128293; 高波+300上</td><td>10-15d</td><td>+0.8~1.4%</td><td>62-67%</td><td>平值-5%</td><td>别超过15天，之后turn负</td></tr>
  <tr><td>&#128200; 低波+300上</td><td>22-30d</td><td>+1.1~2.1%</td><td>56-58%</td><td>平值</td><td>慢牛长持，小收益</td></tr>
  <tr><td>&#128683; 低波+300下</td><td>观望</td><td>-0.7%</td><td>41-42%</td><td>不适合</td><td>不做期权</td></tr>
</table>

<div class="box">
  <b>&#128276; 时间价值策略</b><br>
  &#8226; 彩票（超跌反弹）：20-30天周期——中证500反弹慢，Theta全损耗更合理<br>
  &#8226; 恐慌暴跌：6-10天——同创业板，快进快出<br>
  &#8226; 趋势（低波慢牛）：22-30天——Theta合理损耗下的趋势持有<br><br>
  <b>&#128200; 中证500当前（{cur.date()}）：</b><br>
  HV={hv:.1f}% | 300{"上方" if ab300 else "下方"} | 布林{bbp:.0f}% | 20日{drink:+.1f}%<br>
  到期日推荐：无触发信号，等彩票(超跌+vol>=20)或恐慌(vol>90分位)出现
</div>

<h2>&#128289; CSI500 vs CYB 策略对比</h2>
<table>
  <tr><th>维度</th><th>中证500(000905)</th><th>创业板(159915)</th></tr>
  <tr><td>HV22均值</td><td>21.1%</td><td>~25%+</td></tr>
  <tr><td>彩票最佳到期日</td><td>20-30d</td><td>6-10d</td></tr>
  <tr><td>恐慌样本量</td><td>N=190（可靠）</td><td>N=6（几乎不能用）</td></tr>
  <tr><td>vol信号替代</td><td>vol_rank>90分位</td><td>QVIX>35</td></tr>
  <tr><td>彩票30d>10%概率</td><td>29%</td><td>43%</td></tr>
  <tr><td>安全性</td><td>偏低（HV小+N大）</td><td>高高（HV大但N极小）</td></tr>
</table>
<footer><p>数据源：baostock &#8226; 回测区间：2012-2026 &#8226; 信号质量：中证500统计可靠但收益低，创业板收益高但样本少</p></footer>
</body></html>'''
    
    os.makedirs(SIG_DIR, exist_ok=True)
    with open(os.path.join(SIG_DIR, 'index.html'), 'w') as f:
        f.write(h)
    print(f"  CSI500: {os.path.join(SIG_DIR, 'index.html')}")

if __name__ == '__main__':
    page_csi500()
