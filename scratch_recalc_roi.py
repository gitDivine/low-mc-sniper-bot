import pandas as pd
from src.data_puller.api_client import api_client
import asyncio

async def test_roi():
    df = pd.read_csv("C:/Users/njoku/Downloads/resolved_tokens (3).csv")
    
    target_addrs = [
        "J6LSivR3nt1LajG9TLaf8mvaGduSe6x4QXrsRDt1gsDz", # MTOV
        "4StqN9BQiQxzXTPVKfVfkyWXoh2DtuAo4dCQZ1otdiiT", # HTZ
        "BBxqYTrCKQTXBZ26oZRhvPsayJxqnBWu454EkTH2Gq4x", # GG
        "7yQhT7kt8LzFh6uFhWaKCXJhfCpnXiAiGRfJQeRhWoL9", # PF
        "F2z5Q3q9ujRGwwUSjCiN7cxmDQKyhUtU3KEWvXS5R94z", # Urara
        "dRSx7oCNUP7eRLdrqWqJX4NYVaMa1VetBRJ68AgsGML"  # bCard
    ]

    for addr in target_addrs:
        sub = df[df["token_address"] == addr]
        if sub.empty: continue
        r = sub.iloc[0]
        
        t0_price = r["t0_price_usd"]
        t0_liq = r["t0_liquidity_usd"]
        pool_addr = r["pool_address"]
        
        pool_data = await api_client.fetch_geckoterminal_pool('solana', pool_addr)
        tfinal_liq = 0
        tfinal_price = 0
        if pool_data:
            attr = pool_data.get("attributes", {})
            tfinal_price = float(attr.get("base_token_price_usd") or 0.0)
            tfinal_liq = float(attr.get("reserve_in_usd") or 0.0)
            
        is_liquidity_drained = (tfinal_liq < 500.0) or (t0_liq > 0 and (tfinal_liq / t0_liq) < 0.05)
        
        corr_roi = 0.0 if is_liquidity_drained else (tfinal_price / t0_price if t0_price > 0 else 0)
        
        print(f"Token: {r['symbol']:<10} | Raw ROI: {r['roi_24h']:>10.2f}x | Tfinal Liq: ${tfinal_liq:,.2f} | Drained? {is_liquidity_drained} | New ROI: {corr_roi:.2f}x")
        
    await api_client.close()

if __name__ == "__main__":
    asyncio.run(test_roi())
