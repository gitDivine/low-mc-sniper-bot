import asyncio
import httpx
import base58

async def check_orchid_helius():
    token_mint = "3oBxsVUAwnuicYBfS2ucE87riMkGW6fJ3Pc8abJnWZAt"
    helius_api_key = "0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6"
    
    async with httpx.AsyncClient() as client:
        # Get first 100 signatures
        url = f"https://api.helius.xyz/v0/addresses/{token_mint}/transactions?api-key={helius_api_key}&type=SWAP"
        res = await client.get(url)
        if res.status_code != 200:
            print(f"Error fetching txs: {res.text}")
            return
            
        txs = res.json()
        print(f"Found {len(txs)} swap transactions via Helius.")
        
        buy_sizes = []
        for tx in txs:
            # Simplistic: look at tokenTransfers
            transfers = tx.get("tokenTransfers", [])
            for t in transfers:
                if t.get("mint") == token_mint:
                    amount = t.get("tokenAmount", 0)
                    # We don't have price easily here, but if amount is very small, it's micro-buys.
                    # Or look at nativeTransfers to see SOL amount spent
                    sol_transfers = tx.get("nativeTransfers", [])
                    sol_amount = 0
                    for st in sol_transfers:
                        # Assuming the buyer sent SOL to the pool
                        if st.get("amount", 0) > 0:
                            sol_amount += st.get("amount", 0)
                            
                    # Rough SOL spent / 1e9 * $150
                    usd_val = (sol_amount / 1e9) * 150
                    if usd_val > 0:
                        buy_sizes.append(usd_val)
        
        if buy_sizes:
            buy_sizes.sort()
            median = buy_sizes[len(buy_sizes)//2]
            print(f"Sample of {len(buy_sizes)} transfers:")
            print(f"Min: ${min(buy_sizes):.2f}")
            print(f"Max: ${max(buy_sizes):.2f}")
            print(f"Median: ${median:.2f}")
        else:
            print("Could not extract buy sizes.")

if __name__ == "__main__":
    asyncio.run(check_orchid_helius())
