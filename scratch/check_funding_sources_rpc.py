import asyncio
import httpx
import time

async def get_creator_and_funding(token_mint: str, helius_key: str):
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    
    oldest_sig = None
    last_sig = None
    
    async with httpx.AsyncClient() as client:
        while True:
            params = [token_mint, {"limit": 1000}]
            if last_sig:
                params[1]["before"] = last_sig
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": params}
            res = await client.post(rpc_url, json=payload)
            sigs = res.json().get("result", [])
            if not sigs: break
            oldest_sig = sigs[-1]["signature"]
            last_sig = oldest_sig
            if len(sigs) < 1000: break
                
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getTransaction", "params": [oldest_sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]}
        res = await client.post(rpc_url, json=payload)
        tx = res.json().get("result")
        
        creator = None
        for acc in tx["transaction"]["message"]["accountKeys"]:
            if acc["signer"]:
                creator = acc["pubkey"]
                break
                
        c_last_sig = None
        c_oldest_sig = None
        c_slot = None
        
        while True:
            params = [creator, {"limit": 1000}]
            if c_last_sig:
                params[1]["before"] = c_last_sig
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": params}
            res = await client.post(rpc_url, json=payload)
            sigs = res.json().get("result", [])
            if not sigs: break
            c_oldest_sig = sigs[-1]["signature"]
            c_slot = sigs[-1]["slot"]
            c_last_sig = c_oldest_sig
            if len(sigs) < 1000: break
                
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getTransaction", "params": [c_oldest_sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]}
        res = await client.post(rpc_url, json=payload)
        tx = res.json().get("result")
        
        funder = None
        if tx and "meta" in tx and tx["meta"]:
            pre_balances = tx["meta"].get("preBalances", [])
            post_balances = tx["meta"].get("postBalances", [])
            acc_keys = [a["pubkey"] for a in tx["transaction"]["message"]["accountKeys"]]
            for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
                if pre > post and i < len(acc_keys):
                    if acc_keys[i] != creator:
                        funder = acc_keys[i]
                        break
        print(f"Token: {token_mint}")
        print(f"Creator: {creator}")
        print(f"Funding Slot: {c_slot}")
        print(f"Funder: {funder}\n")

async def main():
    helius_key = "0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6"
    tokens = {
        "giver": "83GeM2UqCJFAa86tcyYacDB9TgaD1vra4vHunuXjpWjq",
        "GIPP": "CXoJFn8PQYfFbq1Svz8hYjhniwvbD1MfPckzb8VNMMHT",
        "GOZMO": "5LV4xvdkCBXCwAq9ehmhBkhwtFMjgq8XFdWxhWv3pump"
    }
    for name, mint in tokens.items():
        await get_creator_and_funding(mint, helius_key)
        time.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
