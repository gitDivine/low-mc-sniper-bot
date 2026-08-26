import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from src.data_puller.api_client import api_client

async def main():
    # Example token: UP (one of the passed rugs from earlier)
    # Actually, I don't have the mint of UP off hand. Let's just pick a random token mint or fetch one from the CSV.
    import pandas as pd
    df = pd.read_csv("scratch/resolved_tokens_48h.csv")
    passed_rugs = df[(df['outcome_label'] == 'Rug / dead') & (df['symbol'] == 'UP')]
    
    if len(passed_rugs) == 0:
        passed_rugs = df[df['outcome_label'] == 'Rug / dead']
        
    token_address = passed_rugs.iloc[0]['token_address']
    symbol = passed_rugs.iloc[0]['symbol']
    print(f"Testing Birdeye swap fetch on {symbol} ({token_address})")
    
    swaps = await api_client.fetch_birdeye_swaps(token_address, max_pages=1)
    
    print(f"Fetched {len(swaps)} swaps from page 1.")
    if swaps:
        print("Sample swap:")
        print(json.dumps(swaps[0], indent=2))
    
    await api_client.close()

if __name__ == "__main__":
    asyncio.run(main())
