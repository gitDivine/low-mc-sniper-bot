import asyncio
from src.evaluator.scorer import OfflineScorer, TokenSnapshotRecord
from datetime import datetime, timezone

async def test():
    scorer = OfflineScorer()
    
    # 1. A token that passes everything but is missing forensic data
    dummy = TokenSnapshotRecord(
        pool_address="test_skip_1",
        token_address="test_skip_1",
        symbol="SKIP1",
        name="Skip Token",
        raw_symbol="SKIP1",
        network="solana",
        chain="solana",
        created_at_utc="2024-01-01T00:00:00Z",
        t0_timestamp=0,
        t0_date="2024-01-01T00:00:00Z",
        age_hours=0.25, # 15 mins (Passes gate 14)
        t0_price_usd=0.01,
        t0_liquidity_usd=10000.0,
        t0_mcap_usd=50000.0, # Death zone - wait, make it 10k for Micro Mode
        t0_volume_usd_15m=10000.0,
        t0_buy_sell_ratio=2.0, # Passes gate 7 (Micro requires > 0.5)
        t0_top10_holder_pct=15.0, # Passes gate 4
        t0_dev_wallet_pct=1.0, # Passes gate 5
        t0_lp_locked_days=365, # Passes gate 1
        t0_is_token_2022=False, # Passes gate 11a
        t0_has_malicious_extensions=False, # Passes gate 11b
        t0_has_rtl_scam=False, # Passes gate 3 (proxy)
        t0_holder_count_exact=120, # Passes gate 6
        t0_holder_count_floor=120, # Passes gate 6
        t0_holder_count=120,
        
        # Missing/placeholder forensic fields
        t0_single_wallet_vol_pct=0.0,
        pool_slot=0,
        creator_funding_slot=0,
        t0_unique_buyers=0,
        t0_median_buy_size_usd=0.0,
        t0_churn_volume_usd=0.0,
    )
    
    # Force Micro Mode
    dummy.t0_mcap_usd = 20000.0 # $20k is in Micro Mode ($5k-$30k)
    dummy.t0_liquidity_usd = 15000.0 # Ratio = 0.75, passes Gate 9 (0.05-5.0)
    
    scored = scorer.evaluate_single(dummy)
    print(f"Passed all gates: {scored.passed_all_gates}")
    print(f"Outcome annotation: {scored.first_failed_gate}")
    if not scored.passed_all_gates:
        print(f"Failed at: {scored.first_failed_gate}")
        
    print(f"Gate 8: {scored.gate_8_single_wallet_vol}")
    print(f"Gate 10: {scored.gate_10_unique_buyers}")
    print(f"Gate 12: {scored.gate_12_funding_cluster}")
    print(f"Gate 13: {scored.gate_13_volume_sanity}")

asyncio.run(test())
