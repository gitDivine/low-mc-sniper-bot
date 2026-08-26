import asyncio
import json
from src.data_puller.api_client import api_client
import statistics
import os
from dotenv import load_dotenv

load_dotenv("C:/Users/njoku/low-mc-sniper-bot/.env")

async def check_orchid():
    token_address = "3oBxsVUAwnuicYBfS2ucE87riMkGW6fJ3Pc8abJnWZAt"
    launch_ts = 1787539200
    
    print(f"Fetching swaps for {token_address}...")
    swaps = await api_client.fetch_birdeye_swaps(token_address, launch_ts)
    await api_client.close()
    print(f"Fetched {len(swaps)} swaps.")
    
    if not swaps:
        print("No swaps found!")
        return
        
    buy_sizes_usd = []
    
    # Let's look at the first 5 buys to see what they look like
    printed = 0
    for s in swaps:
        if s.get("type") == "buy":
            usd_vol = float(s.get("volumeUSD", 0))
            if usd_vol == 0:
                # Calculate manually if Birdeye provided 0
                tokens = float(s.get("uiAmount", 0))
                price = float(s.get("price", 0))
                usd_vol = tokens * price
                
            buy_sizes_usd.append(usd_vol)
            
            if printed < 5:
                print(f"Buy Sample {printed+1}: tokens={s.get('uiAmount')} price={s.get('price')} usd_vol={usd_vol} raw_volumeUSD={s.get('volumeUSD')}")
                printed += 1
                
    if buy_sizes_usd:
        median_buy = statistics.median(buy_sizes_usd)
        print(f"\nTotal Buys: {len(buy_sizes_usd)}")
        print(f"Median Buy Size (USD): ${median_buy:.4f}")
        print(f"Min Buy Size: ${min(buy_sizes_usd):.4f}")
        print(f"Max Buy Size: ${max(buy_sizes_usd):.4f}")
        print(f"Avg Buy Size: ${sum(buy_sizes_usd)/len(buy_sizes_usd):.4f}")
    else:
        print("No buys found.")

if __name__ == "__main__":
    asyncio.run(check_orchid())
