import asyncio
import pandas as pd
from src.evaluator.scorer import OfflineScorer
from src.data_puller.harvester import TokenSnapshotRecord
import math

async def analyze_batch():
    print("Loading data...")
    df = pd.read_csv("scratch/resolved_tokens_batch12.csv")
    
    # Filter only RESOLVED tokens
    df = df[df['status'] == 'RESOLVED'].copy()
    
    records = []
    for _, row in df.iterrows():
        d = row.to_dict()
        for k, v in d.items():
            if isinstance(v, float) and math.isnan(v):
                d[k] = None
                
        # Fix schema mappings
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
        except Exception as e:
            pass

    print(f"Loaded {len(records)} tokens for scoring.")
    scorer = OfflineScorer()
    scored_records = scorer.evaluate_all(records)
    
    # Isolate tokens that ACTUALLY have forensics collected
    forensics_records = [r for r in scored_records if r.t0_forensics_collected]
    print(f"\nTokens with Forensics Collected: {len(forensics_records)}")
    
    winners = [r for r in forensics_records if r.outcome_label == 'Winner']
    rugs = [r for r in forensics_records if r.outcome_label == 'Rug / dead']
    
    print(f"\nBreakdown of Forensics Batch:")
    print(f"  Winners: {len(winners)}")
    print(f"  Rugs / dead: {len(rugs)}")
    
    def print_gate_stats(name, gate_field):
        w_pass = sum(1 for r in winners if getattr(r, gate_field))
        r_pass = sum(1 for r in rugs if getattr(r, gate_field))
        print(f"  {name}:")
        if len(winners) > 0: print(f"    Winners pass rate: {w_pass}/{len(winners)} ({w_pass/len(winners)*100:.1f}%)")
        if len(rugs) > 0: print(f"    Rugs pass rate: {r_pass}/{len(rugs)} ({r_pass/len(rugs)*100:.1f}%)")

    print("\n=== FORENSIC GATE PERFORMANCE ===")
    print_gate_stats("Gate 8 (Whale Vol <= 25%)", "gate_8_single_wallet_vol")
    print_gate_stats("Gate 10 (Unique Buyers >= 20)", "gate_10_unique_buyers")
    print_gate_stats("Gate 13 (Median Buy Size >= $7.5)", "gate_13_volume_sanity")
    
    print("\n=== PRE-FORENSIC GATE PERFORMANCE (for comparison) ===")
    print_gate_stats("Gate 4 (Top 10 <= 20%)", "gate_4_top10_holder")
    print_gate_stats("Gate 5 (Dev <= 3%)", "gate_5_dev_wallet")
    
    # Check Sybil Rugs specifically: Rugs that PASS Gate 4/5 but FAIL forensics
    sophisticated_rugs = [r for r in rugs if r.gate_4_top10_holder and r.gate_5_dev_wallet]
    print(f"\nSophisticated Rugs (Passed G4 & G5): {len(sophisticated_rugs)}")
    if len(sophisticated_rugs) > 0:
        g8_catch = sum(1 for r in sophisticated_rugs if not r.gate_8_single_wallet_vol)
        g10_catch = sum(1 for r in sophisticated_rugs if not r.gate_10_unique_buyers)
        g13_catch = sum(1 for r in sophisticated_rugs if not r.gate_13_volume_sanity)
        any_catch = sum(1 for r in sophisticated_rugs if not (r.gate_8_single_wallet_vol and r.gate_10_unique_buyers and r.gate_13_volume_sanity))
        print(f"  Caught by Gate 8: {g8_catch} ({g8_catch/len(sophisticated_rugs)*100:.1f}%)")
        print(f"  Caught by Gate 10: {g10_catch} ({g10_catch/len(sophisticated_rugs)*100:.1f}%)")
        print(f"  Caught by Gate 13: {g13_catch} ({g13_catch/len(sophisticated_rugs)*100:.1f}%)")
        print(f"  Caught by ANY Forensic Gate: {any_catch} ({any_catch/len(sophisticated_rugs)*100:.1f}%)")

    passed_all = [r for r in forensics_records if r.passed_all_gates]
    passed_winners = [r for r in passed_all if r.outcome_label == 'Winner']
    passed_rugs = [r for r in passed_all if r.outcome_label == 'Rug / dead']

    print("\n=== OVERALL PIPELINE (Forensics subset) ===")
    print(f"Total passing all gates: {len(passed_all)}")
    print(f"  Winners: {len(passed_winners)}")
    print(f"  Rugs: {len(passed_rugs)}")
    
    print("\n=== WINNERS THAT FAILED FORENSICS ===")
    failed_winners = [r for r in winners if not r.passed_all_gates]
    for r in failed_winners:
        print(f"Winner: {r.name} (MCap: ${r.t0_mcap_usd:,.0f})")
        print(f"  First Failed Gate: {r.first_failed_gate}")
        print(f"  Gate 8 (Whale Vol <= 25%): {r.gate_8_single_wallet_vol} (Actual: {r.t0_single_wallet_vol_pct:.1f}%)")
        print(f"  Gate 10 (Unique Buyers >= 20): {r.gate_10_unique_buyers} (Actual: {r.t0_unique_buyers})")
        print(f"  Gate 13 (Median Buy >= $7.5): {r.gate_13_volume_sanity} (Actual: ${getattr(r, 't0_median_buy_size_usd', 0.0):.2f})")
        
    print("\n=== RUGS THAT PASSED ALL GATES (Sample of 5) ===")
    for r in passed_rugs[:5]:
        print(f"Rug: {r.name} ({r.token_address}) (MCap: ${r.t0_mcap_usd:,.0f})")
        print(f"  Gate 4 Top10: {r.t0_top10_holder_pct:.1f}% | Gate 5 Dev: {r.t0_dev_wallet_pct:.1f}%")
        print(f"  Gate 8 Whale Vol: {r.t0_single_wallet_vol_pct:.1f}% | Gate 10 Buyers: {r.t0_unique_buyers} | Gate 13 Median: ${getattr(r, 't0_median_buy_size_usd', 0.0):.2f}")
    
if __name__ == "__main__":
    asyncio.run(analyze_batch())
