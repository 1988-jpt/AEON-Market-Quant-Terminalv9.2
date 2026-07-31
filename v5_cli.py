"""CLI V6 de datos, validación y preproducción."""
from __future__ import annotations
import argparse,asyncio,json
from binance_client import BinanceClient
from order_book import analyze_order_book
from futures_market import FuturesMarketClient
from validation_campaign import CampaignStore
from stress_recovery import run_stress,FaultInjector

def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
 d=sub.add_parser("depth"); d.add_argument("symbol",nargs="?",default="BTC/USDT")
 f=sub.add_parser("futures"); f.add_argument("symbol",nargs="?",default="BTCUSDT")
 c=sub.add_parser("compare"); c.add_argument("symbol",nargs="?",default="BTC/USDT"); c.add_argument("--db",default="data/validation_campaigns.db")
 st=sub.add_parser("stress"); st.add_argument("--attempts",type=int,default=100); st.add_argument("--failure-rate",type=float,default=.2)
 args=p.parse_args()
 if args.cmd=="futures": print(json.dumps(FuturesMarketClient().snapshot(args.symbol).__dict__,indent=2))
 elif args.cmd=="compare": print(json.dumps(CampaignStore(args.db).compare(args.symbol),indent=2))
 elif args.cmd=="stress": print(json.dumps(run_stress(lambda: True,args.attempts,3,FaultInjector(args.failure_rate)).__dict__,indent=2))
 else:
  async def run():
   c=BinanceClient()
   try:
    book=await c.fetch_order_book(args.symbol,100); print(json.dumps(analyze_order_book(book["bids"],book["asks"]).__dict__,indent=2))
   finally: await c.close()
  asyncio.run(run())
if __name__=="__main__":main()
