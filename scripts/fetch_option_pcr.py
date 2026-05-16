"""
深交所 ETF 期权 PCR 数据下载 (159915 创业板ETF)
支持增量更新：已有 CSV 则只补充缺失日期
首次运行自动拉取 2023-01-01 至最新的全部数据
"""

import requests, io, pandas as pd, os, time, warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CSV_PATH = os.path.join(DATA_DIR, "option_pcr.csv")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.szse.cn/market/option/optionQuotation/index.html"
}
base_url = "https://www.szse.cn/api/report/ShowReport"

def load_existing():
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()
    df = pd.read_csv(CSV_PATH)
    if len(df) == 0:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'])
    n = len(df)
    print(f"现有CSV: {n}条 ({df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')})")
    return df

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    existing = load_existing()
    existing_dates = set(existing['date'].dt.strftime('%Y-%m-%d').tolist()) if len(existing) > 0 else set()
    
    today = datetime.now()
    all_dates = pd.bdate_range(start='2023-01-01', end=today.strftime('%Y-%m-%d'))
    
    needed = [d for d in all_dates if d.strftime('%Y-%m-%d') not in existing_dates]
    
    if not needed:
        print("数据已是最新")
        return
    
    print(f"需要下载 {len(needed)} 天")
    
    new_records = []
    successes = 0
    failures = 0
    
    for i, dt in enumerate(needed):
        date_str = dt.strftime('%Y-%m-%d')
        params = {
            "SHOWTYPE": "xlsx",
            "CATALOGID": "option_jycchztj",
            "TABKEY": "tab1",
            "txtSearchDate": date_str,
            "random": "0.1"
        }
        try:
            r = requests.get(base_url, params=params, headers=headers, timeout=20)
            if r.status_code == 200:
                df = pd.read_excel(io.BytesIO(r.content), engine='openpyxl')
                cyb = df[df['标的证券简称(代码)'].str.contains('159915', na=False)]
                if len(cyb) > 0:
                    row = cyb.iloc[0]
                    new_records.append({
                        'date': date_str,
                        'call_vol': int(str(row['认购期权成交量(张)']).replace(',','')),
                        'put_vol': int(str(row['认沽期权成交量(张)']).replace(',','')),
                        'vol_pcr': float(str(row['认沽认购成交比率(%)']).replace(',','')) / 100,
                        'call_oi': int(str(row['认购期权未平仓量(张)']).replace(',','')),
                        'put_oi': int(str(row['认沽期权未平仓量(张)']).replace(',','')),
                        'oi_pcr': float(str(row['认沽认购未平仓比率(%)']).replace(',','')) / 100
                    })
                    successes += 1
        except:
            failures += 1
        
        if (i+1) % 100 == 0:
            print(f"  进度: {i+1}/{len(needed)} 成功{successes} 失败{failures}")
        time.sleep(0.2)
    
    print(f"完成: 成功{successes}天 失败{failures}天")
    
    if new_records:
        new_df = pd.DataFrame(new_records)
        new_df['date'] = pd.to_datetime(new_df['date'])
        combined = pd.concat([existing, new_df], ignore_index=True) if len(existing) > 0 else new_df
        combined = combined.drop_duplicates(subset='date').sort_values('date').reset_index(drop=True)
        combined.to_csv(CSV_PATH, index=False)
        print(f"CSV已保存: {len(combined)}条 ({combined['date'].min().strftime('%Y-%m-%d')} ~ {combined['date'].max().strftime('%Y-%m-%d')})")
        print("最后3条:")
        print(combined.tail(3).to_string(index=False))

if __name__ == "__main__":
    main()
