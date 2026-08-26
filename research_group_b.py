import pandas as pd
import urllib.request
import json
import time
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from config.settings import settings

def rpc_call(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode('utf-8'))

csv_path = 'C:/Users/njoku/Downloads/resolved_tokens (4).csv'
df = pd.read_csv(csv_path)

group_b = df[(df['outcome_label'] == 'Winner') & (df['t0_dev_wallet_pct'] >= 99.0)]
print(f"Found {len(group_b)} Group B tokens.")

tokens = group_b.head(5)['token_address'].tolist()
symbols = group_b.head(5)['symbol'].tolist()

RPC_URL = "https://mainnet.helius-rpc.com/?api-key=0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6"

for sym, mint in zip(symbols, tokens):
    print(f"\n--- Investigating {sym} ({mint}) ---")
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenLargestAccounts",
        "params": [mint]
    }
    resp = rpc_call(RPC_URL, payload)
    
    if "result" not in resp or not resp["result"]["value"]:
        print("Could not fetch largest accounts")
        continue
        
    largest = resp["result"]["value"][0]
    address = largest["address"]
    amount = largest["uiAmount"]
    print(f"Largest account: {address} holding {amount} tokens")
    
    payload2 = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [address, {"encoding": "jsonParsed"}]
    }
    resp2 = rpc_call(RPC_URL, payload2)
    
    if "result" in resp2 and resp2["result"]["value"]:
        owner = resp2["result"]["value"]["owner"]
        print(f"OWNER PROGRAM ID: {owner}")
        
        data = resp2["result"]["value"]["data"]
        if isinstance(data, dict) and "parsed" in data:
            token_owner = data["parsed"]["info"]["owner"]
            print(f"TOKEN ACCOUNT OWNER (Wallet): {token_owner}")
            
            payload3 = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [token_owner, {"encoding": "jsonParsed"}]
            }
            resp3 = rpc_call(RPC_URL, payload3)
            if "result" in resp3 and resp3["result"]["value"]:
                owner_of_owner = resp3["result"]["value"]["owner"]
                print(f"OWNER OF TOKEN ACCOUNT OWNER (The true program managing it): {owner_of_owner}")
    else:
        print("Could not fetch account info")
        
    time.sleep(1)
