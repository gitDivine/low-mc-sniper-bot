import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from src.data_puller.api_client import api_client

async def main():
    url = "https://public-api.birdeye.so/defi/txs/token/seek_by_time"
    params = {
        "address": "ASpbtWALGUicfkpym4UA3CZdy1QehsoA3rLTd3uuVzzS",
        "offset": 0,
        "limit": 5,
        "tx_type": "swap",
        "time_from": 1787355800,
        "time_to": 1787355900
    }
    headers = {"X-API-KEY": os.environ["BIRDEYE_API_KEY"], "x-chain": "solana"}
    
    data = await api_client._get(url, params=params, custom_headers=headers)
    if not data:
        print("No data")
    else:
        items = data.get("data", {}).get("items", [])
        print([t["blockUnixTime"] for t in items])
        
    await api_client.close()

if __name__ == "__main__":
    asyncio.run(main())
