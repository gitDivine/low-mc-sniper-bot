import asyncio
import json
import os
from src.data_puller.api_client import api_client

SOLANA_BURN_ADDRESSES = [
    "1nc1nerator11111111111111111111111111111111",
    "So11111111111111111111111111111111111111112"
]

async def check_lp_burn_status(lp_mint: str) -> tuple[int, bool]:
    lp_supply = await api_client.fetch_solana_token_supply(lp_mint)
    lp_accounts = await api_client.fetch_solana_token_largest_accounts(lp_mint)
    
    t0_lp_locked_days = 0
    is_burned = False
    
    if lp_supply and lp_accounts and lp_supply > 0:
        largest_acc = lp_accounts[0]
        largest_addr = largest_acc["address"]
        largest_amt = largest_acc["uiAmount"]
        
        print(f"    LP Supply: {lp_supply:,.2f}")
        print(f"    Top Holder: {largest_addr} with {largest_amt:,.2f} ({(largest_amt/lp_supply)*100:.2f}%)")
        
        if largest_addr in SOLANA_BURN_ADDRESSES and (largest_amt / lp_supply) >= 0.95:
            t0_lp_locked_days = 365
            is_burned = True
        else:
            for acc in lp_accounts[:3]:
                if acc["address"] in SOLANA_BURN_ADDRESSES and (acc["uiAmount"] / lp_supply) >= 0.80:
                    t0_lp_locked_days = 365
                    is_burned = True
                    break
    return t0_lp_locked_days, is_burned

async def test_tokens():
    harvest_file = "data/raw/raw_harvest_solana_99999999_999999.json"
    if os.path.exists(harvest_file):
        with open(harvest_file, "r") as f:
            pools = json.load(f)
            
        print(f"Scanning for 1 BURNED and 1 UNLOCKED Raydium pool from {len(pools)} harvested pools...")
        found_burned = False
        found_unlocked = False
        
        for pool in pools:
            if found_burned and found_unlocked:
                break
                
            addr = pool["pool_address"]
            sym = pool.get("symbol", "UNKNOWN")
            
            lp_mint = await api_client.fetch_pool_lp_mint(addr)
            if lp_mint:
                locked, burned = await check_lp_burn_status(lp_mint)
                
                if burned and not found_burned:
                    print(f"\\n[PASSED GATE 1] Verified BURNED Token:")
                    print(f"Token: {sym}")
                    print(f"Pool: {addr} | LP Mint: {lp_mint}")
                    found_burned = True
                elif not burned and not found_unlocked:
                    print(f"\\n[FAILED GATE 1] Verified UNLOCKED Token:")
                    print(f"Token: {sym}")
                    print(f"Pool: {addr} | LP Mint: {lp_mint}")
                    found_unlocked = True

asyncio.run(test_tokens())
