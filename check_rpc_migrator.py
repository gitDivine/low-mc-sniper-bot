import asyncio
import httpx
import time
from datetime import datetime, timezone

async def main():
    migrator = "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg" # Pump.fun Raydium Migrator
    url = "https://solana-rpc.publicnode.com"
    
    four_hours_ago = int(time.time()) - (4 * 3600)
    
    signatures = []
    before = None
    
    print(f"Fetching Pump.fun Migrations since {datetime.fromtimestamp(four_hours_ago, timezone.utc)}...")
    
    async with httpx.AsyncClient() as client:
        while True:
            params = [{"limit": 1000}]
            if before:
                params[0]["before"] = before
                
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [migrator, params[0]]
            }
            
            res = await client.post(url, json=payload, timeout=20.0)
            data = res.json()
            sigs = data.get("result", [])
            
            if not sigs:
                break
                
            valid = []
            for s in sigs:
                if not s.get("err") and s.get("blockTime") and s["blockTime"] >= four_hours_ago:
                    valid.append(s)
            
            signatures.extend(valid)
            last_sig = sigs[-1]
            before = last_sig["signature"]
            last_time = last_sig.get("blockTime")
            
            print(f"Fetched {len(sigs)} signatures. Valid in window: {len(valid)}. Last time: {datetime.fromtimestamp(last_time, timezone.utc) if last_time else 'Unknown'}")
            
            if last_time and last_time < four_hours_ago:
                break
                
            await asyncio.sleep(0.5)
            
    print(f"Total Pump.fun migrations to Raydium in last 4 hours (RPC): {len(signatures)}")

if __name__ == "__main__":
    asyncio.run(main())
