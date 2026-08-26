import asyncio
import httpx
import time
from datetime import datetime, timezone

async def main():
    fee_account = "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eqaYcHQqtj2G5" # Raydium v4 Create Pool Fee Account
    url = "https://solana-rpc.publicnode.com"
    
    four_hours_ago = int(time.time()) - (4 * 3600)
    
    signatures = []
    before = None
    
    print(f"Fetching Raydium v4 pool creations since {datetime.fromtimestamp(four_hours_ago, timezone.utc)}...")
    
    async with httpx.AsyncClient() as client:
        while True:
            params = [{"limit": 1000}]
            if before:
                params[0]["before"] = before
                
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [fee_account, params[0]]
            }
            
            res = await client.post(url, json=payload, timeout=20.0)
            data = res.json()
            sigs = data.get("result", [])
            
            if not sigs:
                break
                
            signatures.extend(sigs)
            last_sig = sigs[-1]
            before = last_sig["signature"]
            last_time = last_sig.get("blockTime")
            
            print(f"Fetched {len(sigs)} signatures. Last time: {datetime.fromtimestamp(last_time, timezone.utc) if last_time else 'Unknown'}")
            
            if last_time and last_time < four_hours_ago:
                break
                
            await asyncio.sleep(0.5)
            
    # Filter for last 4 hours
    valid_sigs = [s for s in signatures if s.get("blockTime") and s["blockTime"] >= four_hours_ago]
    print(f"Total Raydium v4 pools created in last 4 hours (RPC): {len(valid_sigs)}")

if __name__ == "__main__":
    asyncio.run(main())
