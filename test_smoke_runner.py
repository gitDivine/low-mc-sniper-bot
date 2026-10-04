import asyncio
import json
from src.data_puller.api_client import api_client
from src.shadow.runner import ShadowRunner

async def main():
    print("Fetching latest pool from GeckoTerminal...")
    pools = await api_client.fetch_geckoterminal_new_pools('solana', page=1)
    if not pools:
        print("Failed to fetch pools.")
        return
        
    pool = pools[0]
    name = pool.get('attributes', {}).get('name', 'Unknown')
    address = pool.get('attributes', {}).get('address', 'Unknown')
    print(f"Testing against pool: {name} ({address})")
    
    runner = ShadowRunner('solana')
    
    print("Capturing T0 Snapshot...")
    try:
        # Avoid charmap error on windows console
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        
        symbol = pool.get('attributes', {}).get('name', 'Unknown').split(' / ')[0]
        
        # NOTE: We inject artificial bounds (mcap=20k, liq=15k, vol=5k) here to intentionally 
        # bypass the Gate 9/11 'Out of bounds' check. This means this smoke test validates 
        # the Gate 3 (Rugcheck) and Gate 12 (RPC) integrations, but it does NOT verify the 
        # bounding logic itself. 
        snapshot = await runner._capture_t0_snapshot(
            pool_address=pool.get('attributes', {}).get('address', 'Unknown'),
            token_address=pool.get('relationships', {}).get('base_token', {}).get('data', {}).get('id', '').replace('solana_', ''),
            symbol=symbol,
            price_usd=0.0001,
            liquidity_usd=15000.0,
            mcap_usd=20000.0,
            vol_15m=5000.0,
            age_hours=0.25,
            has_rtl_scam=False,
            forensics={}
        )
        print("\n=== SUCCESS: Snapshot Created ===")
        
        print(json.dumps(snapshot, indent=2))
        
        # Verify specific fields
        print("\n=== VERIFICATION ===")
        if snapshot.get("drop_reason") == "data_incomplete_rugcheck":
            print("[FAIL] Still dropping due to missing Rugcheck data.")
        elif "t0_rugcheck_risks" in snapshot:
            print(f"[PASS] Rugcheck data retrieved successfully. Risks: {snapshot.get('t0_rugcheck_risks')}")
        else:
            print("[FAIL] t0_rugcheck_risks field missing from snapshot.")
            
    except Exception as e:
        print(f"\n❌ CRITICAL FAILURE: Exception during snapshot creation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
