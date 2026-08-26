import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.evaluator.scorer import OfflineScorer

def main():
    scorer = OfflineScorer()
    # 1. Load dataset
    filepath = Path(r"C:\Users\njoku\Downloads\resolved_tokens (8).csv")
    
    # Adjust settings specifically for this verification batch to ignore missing/legacy data
    # NOTE: We only bypass Gate 10 and Gate 13 because the fields (t0_unique_buyers, t0_median_buy_size_usd) 
    # were not captured in Batch 8. We MUST test the actual approved thresholds for all other gates.
    from config.settings import settings
    settings.GATE_10_MIN_UNIQUE_BUYERS = 0  # Missing from batch 8
    
    # We load the dataset with the built-in parser so all fields (like holders) are properly populated.
    all_records = scorer.load_dataset(filepath)
    
    # Bypass Gate 13 missing fields in this dataset
    for r in all_records:
        r.t0_median_buy_size_usd = 999.0
        r.t0_churn_volume_usd = 0.0
    
    # Filter only resolved ones if they have outcome_label (which they do)
    # The actual outcome_label parsing already happens in load_dataset
    records = [r for r in all_records if getattr(r, 'outcome_label', '') != '']
        
    # 2. Score all
    scored = scorer.evaluate_all(records)
    
    # 3. Create DataFrame
    df = pd.DataFrame([r.model_dump() for r in scored])
    
    # Remove the `status` filter, we already filtered by outcome_label above
    
    print("\n" + "="*50)
    print("PIPELINE VERIFICATION")
    print("="*50)
    
    # A) Check Winner Retention
    winners = df[df['outcome_label'] == 'Winner']
    
    micro_winners = winners[(winners['t0_mcap_usd'] >= 5000) & (winners['t0_mcap_usd'] <= 30000)]
    micro_passed = micro_winners[micro_winners['passed_all_gates'] == True]
    print(f"Micro Winners Passed: {len(micro_passed)} / {len(micro_winners)}")
    if len(micro_passed) < len(micro_winners):
        print("Micro Winners Failed Gates:")
        print(micro_winners[micro_winners['passed_all_gates'] == False]['first_failed_gate'].value_counts())
    
    grad_winners = winners[(winners['t0_mcap_usd'] >= 150000) & (winners['t0_mcap_usd'] <= 500000)]
    grad_passed = grad_winners[grad_winners['passed_all_gates'] == True]
    print(f"Graduate Winners Passed: {len(grad_passed)} / {len(grad_winners)}")
    if len(grad_passed) < len(grad_winners):
        print("Graduate Winners Failed Gates:")
        print(grad_winners[grad_winners['passed_all_gates'] == False]['first_failed_gate'].value_counts())
    
    # B) Check Graduate Scams
    grad_scams = df[(df['outcome_label'] == 'Scam / washed') & 
                    (df['t0_mcap_usd'] >= 150000) & 
                    (df['t0_mcap_usd'] <= 500000)]
    grad_scams_passed = grad_scams[grad_scams['passed_all_gates'] == True]
    print(f"Graduate Scams Passed: {len(grad_scams_passed)} / {len(grad_scams)} (Expected: 0)")
    
    if len(grad_scams_passed) > 0:
        print("WARNING: Graduate Scams that passed:")
        print(grad_scams_passed[['t0_mcap_usd', 't0_liquidity_usd', 'first_failed_gate']])
        
    # C) Check Death-Zone Rugs
    dz_rugs = df[(df['outcome_label'] == 'Rug / dead') & 
                 (df['t0_mcap_usd'] >= 30000) & 
                 (df['t0_mcap_usd'] <= 100000)]
    # Wait, earlier we checked 30k-100k for the 1,483 figure, though the mode gap is 30k-150k. 
    # Let's check 30k-100k specifically to match the 1,483 number.
    dz_rugs_passed = dz_rugs[dz_rugs['passed_all_gates'] == True]
    print(f"Death Zone ($30k-$100k) Rugs Passed: {len(dz_rugs_passed)} / {len(dz_rugs)} (Expected: 0)")
    
    if len(dz_rugs_passed) > 0:
        print("WARNING: Death Zone Rugs that passed:")
        print(dz_rugs_passed[['t0_mcap_usd', 'first_failed_gate']])

    print("\n" + "="*50)
    print("FINAL CALIBRATION SUMMARY")
    print("="*50)
    print(scorer.generate_calibration_report())

if __name__ == "__main__":
    main()
