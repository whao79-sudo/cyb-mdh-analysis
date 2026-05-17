#!/usr/bin/env python3
"""
创业板ETF (159915) QVIX 隐含波动率数据下载
使用 AKShare 获取中证指数公司发布的创业板ETF QVIX
数据来源: 中证指数有限公司
"""
import pandas as pd
import os, sys
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CSV_PATH = os.path.join(DATA_DIR, "qvix_data.csv")

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("📥 下载创业板ETF QVIX (隐含波动率) ...")
    import akshare as ak
    
    df = ak.index_option_cyb_qvix()
    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna(subset=['close'])
    df = df.rename(columns={'open': 'qvix_open', 'high': 'qvix_high', 'low': 'qvix_low', 'close': 'qvix'})
    df = df.sort_values('date').reset_index(drop=True)
    
    df.to_csv(CSV_PATH, index=False)
    print(f"  ✅ 已保存: {CSV_PATH}")
    print(f"     数据: {df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')} ({len(df)} 条)")
    print(f"     最新QVIX: {df['qvix'].iloc[-1]:.2f}")

if __name__ == "__main__":
    main()
