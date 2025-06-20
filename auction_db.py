import sqlite3
import pandas as pd

DB_NAME = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS auction_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT,
            player TEXT,
            price INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_result(team, player, price):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO auction_results (team, player, price) VALUES (?, ?, ?)', (team, player, price))
    conn.commit()
    conn.close()

def get_results():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT * FROM auction_results', conn)
    conn.close()

    # 🗝️ This forces string columns to decode properly and ignore bad bytes
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).apply(lambda x: x.encode('utf-8', 'ignore').decode('utf-8', 'ignore'))
    return df

def clear_results():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM auction_results')
    conn.commit()
    conn.close()
