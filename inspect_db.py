import sqlite3
import sys

DB = "app_data.db"
if len(sys.argv) > 1:
    DB = sys.argv[1]

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT id, ts, symbol, signal, price, details FROM signals ORDER BY id DESC LIMIT 20")
rows = cur.fetchall()
for r in rows:
    print(r)
conn.close()