import sqlite3
from storage import Storage


def test_migrates_legacy_signal_unique_constraint(tmp_path):
    db = tmp_path / 'legacy.db'
    with sqlite3.connect(db) as conn:
        conn.execute(
            'CREATE TABLE signals('
            'id INTEGER PRIMARY KEY AUTOINCREMENT,'
            'ts INTEGER NOT NULL,symbol TEXT NOT NULL,signal TEXT NOT NULL,'
            'price REAL NOT NULL,details TEXT,UNIQUE(ts,symbol,signal))'
        )
        conn.execute(
            'INSERT INTO signals(ts,symbol,signal,price,details) VALUES(1,\'BTC/USDT\',\'BUY\',10,\'old\')'
        )
        conn.execute(
            'INSERT INTO signals(ts,symbol,signal,price,details) VALUES(1,\'BTC/USDT\',\'HOLD\',11,\'new\')'
        )
        conn.commit()

    storage = Storage(str(db))
    assert storage.insert_signal(1, 'BTC/USDT', 'SELL', 12, 'updated')
    rows = storage.get_recent_signals(10)
    assert len(rows) == 1
    assert rows[0]['signal'] == 'SELL'
    assert rows[0]['price'] == 12
    assert storage.get_metadata('schema_version') == '4'
