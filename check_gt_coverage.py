import asyncio
import httpx
import json

async def main():
    migrator = "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg" 
    rpc_url = "https://solana-rpc.publicnode.com"
    gt_url = "https://api.geckoterminal.com/api/v2/networks/solana/pools/"
    
    print("Fetching last 20 Pump.fun migrations from RPC...")
    
    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [migrator, {"limit": 20}]
        }
        res = await client.post(rpc_url, json=payload, timeout=20.0)
        sigs = res.json().get("result", [])
        
        pools_to_check = []
        for s in sigs:
            if s.get("err"): continue
            
            # Fetch tx to get pool address
            tx_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [s["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            tx_res = await client.post(rpc_url, json=tx_payload)
            tx_data = tx_res.json().get("result", {})
            if not tx_data: continue
            
            # The pool address is usually the account created by Raydium. 
            # In Pump.fun migration, the Raydium AMM ID is the 3rd account or so. 
            # Actually, simpler: we can just check if any account in the tx is on GT.
            account_keys = [acc["pubkey"] for acc in tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])]
            pools_to_check.append(account_keys)
            await asyncio.sleep(0.5)
            
        print(f"Checking {len(pools_to_check)} migrations against GT...")
        
        found = 0
        missing = 0
        
        for keys in pools_to_check:
            # We don't know exactly which key is the pool. We will batch check all keys against GT.
            # GT allows 30 addresses per request.
            batch = ",".join(keys[:30])
            gt_multi = f"https://api.geckoterminal.com/api/v2/networks/solana/pools/multi/{batch}"
            gt_res = await client.get(gt_multi)
            
            if gt_res.status_code == 200:
                data = gt_res.json().get("data", [])
                if len(data) > 0:
                    found += 1
                    continue
            missing += 1
            await asyncio.sleep(1)
            
        print(f"Results: {found} found on GT, {missing} missing from GT.")

if __name__ == "__main__":
    asyncio.run(main())
