import asyncio
import httpx
import time
from datetime import datetime, timezone

async def main():
    url = "https://api.geckoterminal.com/api/v2/networks/solana/new_pools"
    
    four_hours_ago = int(time.time()) - (4 * 3600)
    print(f"Fetching GT pools created since {datetime.fromtimestamp(four_hours_ago, timezone.utc)}...")
    
    total_in_4h = 0
    oldest_seen = int(time.time())
    
    async with httpx.AsyncClient() as client:
        for page in range(1, 11): # test 10 pages
            res = await client.get(url, params={"page": page})
            data = res.json()
            pools = data.get("data", [])
            
            if not pools:
                break
                
            for p in pools:
                created_at = p.get("attributes", {}).get("pool_created_at")
                if created_at:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    ts = int(dt.timestamp())
                    oldest_seen = min(oldest_seen, ts)
                    if ts >= four_hours_ago:
                        total_in_4h += 1
                        
            print(f"Page {page}: Oldest pool on this page: {datetime.fromtimestamp(oldest_seen, timezone.utc)}")
            if oldest_seen < four_hours_ago:
                break
                
            await asyncio.sleep(1)
            
    print(f"Total GT pools created in last 4 hours (across up to 10 pages): {total_in_4h}")
    print(f"Oldest timestamp reached: {datetime.fromtimestamp(oldest_seen, timezone.utc)}")

if __name__ == "__main__":
    asyncio.run(main())
