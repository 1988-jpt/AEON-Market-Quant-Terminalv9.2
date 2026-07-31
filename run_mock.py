import time
from data_analysis import ohlcv_to_df
from strategy import MaCrossStrategy
from storage import Storage
from notifier import LocalNotifier

def generate_mock_ohlcv(n=100, start_price=20000.0, interval_ms=3600*1000):
    now = int(time.time() * 1000)
    ohlcv = []
    price = start_price
    for i in range(n):
        ts = now - (n - 1 - i) * interval_ms
        # simple walk with small noise
        open_p = price + ((i % 5) - 2) * 2
        close_p = open_p + ((-1) ** i) * 3
        high = max(open_p, close_p) + 1.5
        low = min(open_p, close_p) - 1.5
        vol = 0.1 + (i * 0.01)
        ohlcv.append([ts, open_p, high, low, close_p, vol])
        price = close_p
    return ohlcv

def main():
    ohlcv = generate_mock_ohlcv(n=120, start_price=20000.0)
    df = ohlcv_to_df(ohlcv)
    strategy = MaCrossStrategy(short_period=5, long_period=20)
    decision = strategy.decide(df)
    storage = Storage()
    notifier = LocalNotifier()
    ts = int(df.index[-1].timestamp() * 1000)
    storage.insert_signal(ts, "BTC/USDT", decision["signal"], float(df['close'].iloc[-1]), decision.get("reason"))
    notifier.send("Mock Signal", f"{decision['signal']} at {df['close'].iloc[-1]} ({decision.get('reason')})")
    print("Decision:", decision)

if __name__ == "__main__":
    main()