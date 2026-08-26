import asyncio
import pandas as pd
from src.evaluator.scorer import OfflineScorer
from src.data_puller.harvester import TokenSnapshotRecord
import math
from scratch.birdeye_processor import process_birdeye_swaps
from src.data_puller.api_client import api_client
from datetime import datetime, timezone

async def main():
    df = pd.read_csv("scratch/resolved_tokens_48h.csv")
    df = df[df['status'] == 'RESOLVED'].copy()

    records = []
    for _, row in df.iterrows():
        d = row.to_dict()
        for k, v in d.items():
            if isinstance(v, float) and math.isnan(v):
                d[k] = None
        
        exact = d.get('t0_holder_count_exact')
        floor = d.get('t0_holder_count_floor')
        if exact is not None and not pd.isna(exact):
            d['t0_holder_count'] = int(exact)
        elif floor is not None and not pd.isna(floor):
            d['t0_holder_count'] = int(floor)
        else:
            d['t0_holder_count'] = 0
            
        if 'chain' not in d or d['chain'] is None: d['chain'] = d.get('network', 'solana')
        if 'name' not in d or d['name'] is None: d['name'] = d.get('symbol', 'Unknown')
        if 'created_at_utc' not in d or d['created_at_utc'] is None: d['created_at_utc'] = d.get('t0_date', '')
        fc = d.get('t0_forensics_collected')
        if isinstance(fc, str): d['t0_forensics_collected'] = fc.lower() == 'true'
            
        try:
            record = TokenSnapshotRecord(**d)
            records.append(record)
        except Exception:
            pass

    scorer = OfflineScorer()
    scored_records = scorer.evaluate_all(records)

    passed_rugs = [r for r in scored_records if r.passed_all_gates and r.outcome_label == 'Rug / dead']
    
    targets = ["UP", "ANSEM", "life", "Basecat"]
    found = []
    for r in passed_rugs:
        base_sym = r.symbol.split(" (")[0]
        if base_sym in targets and base_sym not in [f.symbol.split(" (")[0] for f in found]:
            found.append(r)
            if len(found) == 4:
                break
                
    for r in found:
        # Re-derive launch timestamp from created_at_utc
        dt = datetime.fromisoformat(r.created_at_utc.replace('Z', '+00:00'))
        launch_ts = int(dt.timestamp()) - 900
        print(f"\n--- Fetching Birdeye for {r.symbol} ({r.token_address}) ---")
        
        swaps = await api_client.fetch_birdeye_swaps(r.token_address, launch_ts, max_pages=5)
        print(f"Fetched {len(swaps)} swaps from Birdeye.")
        
        metrics = process_birdeye_swaps(swaps)
        print("Derived Forensics:")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
            
        # Manually apply gates 8, 10, 13
        passed = True
        
        # Gate 8: Whale Vol <= 25%
        g8 = metrics["t0_single_wallet_vol_pct"] <= 25.0
        print(f"Gate 8 (Whale Vol <= 25%): {'PASS' if g8 else 'FAIL'}")
        
        # Gate 10: Unique Buyers >= 20
        g10 = metrics["t0_unique_buyers"] >= 20
        print(f"Gate 10 (Unique Buyers >= 20): {'PASS' if g10 else 'FAIL'}")
        
        # Gate 13: Median Buy >= $7.5
        g13 = metrics["t0_median_buy_size_usd"] >= 7.5
        print(f"Gate 13 (Median Buy >= $7.5): {'PASS' if g13 else 'FAIL'}")
        
    await api_client.close()
        
if __name__ == "__main__":
    asyncio.run(main())
