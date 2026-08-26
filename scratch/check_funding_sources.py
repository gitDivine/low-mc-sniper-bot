import asyncio
import httpx

async def get_creator_wallet(token_mint: str, helius_key: str) -> str:
    # On Pump.fun, the mint authority is revoked, but the creator is usually the one who made the first swap
    # or the token's metadata update authority.
    # A reliable way: get the first transaction for the token mint.
    url = f"https://api.helius.xyz/v0/addresses/{token_mint}/transactions?api-key={helius_key}"
    
    # We want the oldest transaction, so we need to paginate. But for simplicity, we can fetch
    # the latest, and keep going until there are no more.
    last_sig = None
    oldest_tx = None
    async with httpx.AsyncClient() as client:
        while True:
            u = url
            if last_sig:
                u += f"&before={last_sig}"
            res = await client.get(u)
            if res.status_code != 200:
                break
            txs = res.json()
            if not txs:
                break
            oldest_tx = txs[-1]
            last_sig = oldest_tx["signature"]
            if len(txs) < 50:
                break
                
    if oldest_tx:
        # The fee payer of the very first transaction is usually the creator
        return oldest_tx.get("feePayer")
    return None

async def get_funding_tx(wallet: str, helius_key: str):
    url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key={helius_key}"
    last_sig = None
    oldest_tx = None
    async with httpx.AsyncClient() as client:
        while True:
            u = url
            if last_sig:
                u += f"&before={last_sig}"
            res = await client.get(u)
            if res.status_code != 200:
                break
            txs = res.json()
            if not txs:
                break
            oldest_tx = txs[-1]
            last_sig = oldest_tx["signature"]
            if len(txs) < 50:
                break
    
    if oldest_tx:
        # Look at nativeTransfers to see who funded it
        transfers = oldest_tx.get("nativeTransfers", [])
        funders = []
        for t in transfers:
            if t.get("toUserAccount") == wallet:
                funders.append(t.get("fromUserAccount"))
        return oldest_tx.get("signature"), oldest_tx.get("timestamp"), funders
    return None, None, []

async def analyze():
    helius_key = "0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6"
    tokens = {
        "GOZMO": "5LV4xvdkCBXCwAq9ehmhBkhwtFMjgq8XFdWxhWv3pump",
        "CRYPT": "DMRvAber8hUYJFDZWqMoXjjRNDasU1c5cPYtmt7N4LS6",
        "NINJA": "J1wYDggzvB8Mj7dynpzhHuxk6pqDvPyfouuLzAbnnfe9",
        "giver": "83GeM2UqCJFAa86tcyYacDB9TgaD1vra4vHunuXjpWjq",
        "GIPP": "CXoJFn8PQYfFbq1Svz8hYjhniwvbD1MfPckzb8VNMMHT"
    }
    
    for name, mint in tokens.items():
        print(f"\nAnalyzing {name} ({mint})...")
        creator = await get_creator_wallet(mint, helius_key)
        if not creator:
            print("  Could not find creator.")
            continue
        print(f"  Creator: {creator}")
        
        sig, ts, funders = await get_funding_tx(creator, helius_key)
        print(f"  Funding Tx: {sig}")
        print(f"  Funding Timestamp: {ts}")
        print(f"  Funded By: {funders}")

if __name__ == "__main__":
    asyncio.run(analyze())
