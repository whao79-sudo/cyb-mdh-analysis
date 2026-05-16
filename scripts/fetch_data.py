"""
从 baostock 下载创业板指数 (sz.399006) 日线数据
存储到 SQLite 数据库
每天下载不超过 5 万条
"""

import baostock as bs
import pandas as pd
import sqlite3
import os
import sys
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cyb_data.db")
MAX_ROWS = 50000  # baostock 每日限制

def init_db():
    """初始化数据库，创建表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            amount REAL,
            pe REAL,
            pb REAL,
            turnover REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")

def get_existing_dates():
    """获取数据库中已有的日期"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT date FROM daily ORDER BY date", conn)
    conn.close()
    return set(df['date'].tolist())

def fetch_and_store(start_date="2024-01-01", end_date=None):
    """从 baostock 下载数据并存入数据库"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    # 登录
    lg = bs.login()
    if lg.error_code != '0':
        print(f"❌ baostock 登录失败: {lg.error_msg}")
        return False
    print(f"✅ baostock 登录成功")
    
    existing_dates = get_existing_dates()
    print(f"📊 已有 {len(existing_dates)} 条记录")
    
    # 获取创业板指数日线数据
    rs = bs.query_history_k_data_plus(
        "sz.399006",
        "date,open,high,low,close,volume,amount,peTTM,pbMRQ,turn",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3"  # 不复权（指数不需要复权）
    )
    
    if rs.error_code != '0':
        print(f"❌ 数据查询失败: {rs.error_msg}")
        bs.logout()
        return False
    
    # 转换为 DataFrame
    rows = []
    while rs.next():
        row = rs.get_row_data()
        rows.append(row)
    
    df = pd.DataFrame(rows, columns=['date','open','high','low','close','volume','amount','pe','pb','turnover'])
    
    # 过滤已有数据
    new_df = df[~df['date'].isin(existing_dates)].copy()
    
    # 限制每天不超过 5 万条
    if len(new_df) > MAX_ROWS:
        print(f"⚠️ 新数据 {len(new_df)} 条超过每日限制 {MAX_ROWS}，截取前 {MAX_ROWS} 条")
        new_df = new_df.head(MAX_ROWS)
    
    if len(new_df) == 0:
        print("📭 没有新数据需要更新")
        bs.logout()
        return True
    
    # 数据清洗
    for col in ['open','high','low','close','volume','amount','pe','pb','turnover']:
        new_df[col] = pd.to_numeric(new_df[col], errors='coerce')
    
    # 存入数据库
    conn = sqlite3.connect(DB_PATH)
    new_df.to_sql('daily', conn, if_exists='append', index=False)
    conn.close()
    
    print(f"📥 新增 {len(new_df)} 条数据 (范围: {new_df['date'].min()} ~ {new_df['date'].max()})")
    bs.logout()
    return True

def get_data_from_db(start_date="2010-06-01", end_date=None):
    """从数据库读取数据"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT * FROM daily WHERE date >= '{start_date}' AND date <= '{end_date}' ORDER BY date"
    df = pd.read_sql(query, conn)
    conn.close()
    
    # 确保数值类型正确
    for col in ['open','high','low','close','volume','amount','pe','pb','turnover']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print(f"📊 从数据库读取 {len(df)} 条数据 ({start_date} ~ {end_date})")
    return df

if __name__ == "__main__":
    init_db()
    start = sys.argv[1] if len(sys.argv) > 1 else "2010-06-01"
    end = sys.argv[2] if len(sys.argv) > 2 else None
    fetch_and_store(start, end)
