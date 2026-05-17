#!/usr/bin/env python3
"""每日更新 QVIX 波动率套利策略信号"""
import pandas as pd, numpy as np, akshare as ak, json, os, warnings
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

df_q = ak.index_option_cyb_qvix()
df_q['date'] = pd.to_datetime(df_q['date'])
df_q = df_q.dropna(subset=['close'])
df_q.rename(columns={'close':'qvix'}, inplace=True)
df_q = df_q.set_index('date').sort_index()

m = df_q[['qvix']].copy()
m['qvix_pct_60'] = m['qvix'].rolling(60).rank(pct=True)
m['fwd_10d_chg'] = m['qvix'].shift(-10) - m['qvix']
m['opt_ret'] = m['fwd_10d_chg'] * 5

buy_sig = (m['qvix_pct_60'] >= 0.15) & (m['qvix_pct_60'] <= 0.30)
sell_sig = (m['qvix_pct_60'] >= 0.40) & (m['qvix_pct_60'] <= 0.60)

today = m.index[-1].strftime('%Y-%m-%d')
now_v = round(m['qvix'].iloc[-1], 1)
now_pct_60 = int(m['qvix_pct_60'].iloc[-1] * 100)
now_pct_all = int(m['qvix'].rank(pct=True).iloc[-1] * 100)

cur_buy = bool(buy_sig.iloc[-1])
cur_sell = bool(sell_sig.iloc[-1])

buy_sub = m[buy_sig].dropna(subset=['fwd_10d_chg'])
sell_sub = m[sell_sig].dropna(subset=['fwd_10d_chg'])

ret = {
    'latest_qvix': now_v,
    'latest_date': today,
    'qvix_pct_60': now_pct_60,
    'qvix_pct_all': now_pct_all,
    'current_signal': '买入期权' if cur_buy else ('卖出期权(卖方)' if cur_sell else '无信号'),
    'buy_signal': cur_buy,
    'sell_signal': cur_sell,
    'buy_backtest': {
        'total': int(len(buy_sub)),
        'avg_delta_qvix_10d': round(buy_sub['fwd_10d_chg'].mean(), 2),
        'avg_opt_ret_10d': round(buy_sub['opt_ret'].mean(), 1),
        'win_rate': int((buy_sub['fwd_10d_chg'] > 0).mean() * 100),
    },
    'sell_backtest': {
        'total': int(len(sell_sub)),
        'avg_delta_qvix_10d': round(sell_sub['fwd_10d_chg'].mean(), 2),
        'avg_opt_ret_10d': round(sell_sub['opt_ret'].mean(), 1),
        'win_rate': int((sell_sub['fwd_10d_chg'] < 0).mean() * 100),
    },
}

# 最近信号
buy_dates = m[buy_sig].index[-10:]
sell_dates = m[sell_sig].index[-10:]
ret['recent_buy_signals'] = []
ret['recent_sell_signals'] = []

for d in buy_dates[-5:]:
    r = m.loc[d]
    fwd = r['fwd_10d_chg']
    opt = r['opt_ret']
    ret['recent_buy_signals'].append({
        'date': d.strftime('%Y-%m-%d'),
        'qvix': round(r['qvix'], 1),
        'pct': int(r['qvix_pct_60'] * 100),
        'fwd_delta_qvix': round(fwd, 2) if pd.notna(fwd) else None,
        'opt_ret': round(opt, 1) if pd.notna(opt) else None,
    })

for d in sell_dates[-5:]:
    r = m.loc[d]
    fwd = r['fwd_10d_chg']
    opt = r['opt_ret']
    ret['recent_sell_signals'].append({
        'date': d.strftime('%Y-%m-%d'),
        'qvix': round(r['qvix'], 1),
        'pct': int(r['qvix_pct_60'] * 100),
        'fwd_delta_qvix': round(fwd, 2) if pd.notna(fwd) else None,
        'opt_ret': round(opt, 1) if pd.notna(opt) else None,
    })

out = os.path.join(DATA_DIR, "qvix_strategy.json")
with open(out, 'w', encoding='utf-8') as f:
    json.dump(ret, f, indent=2, ensure_ascii=False)

print(f"✅ QVIX策略信号已更新: {today} | QVIX={now_v}% | 分位={now_pct_60}% | 信号={ret['current_signal']}")
