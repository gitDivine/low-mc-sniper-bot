import pandas as pd
from src.evaluator.scorer import OfflineScorer
from src.data_puller.harvester import TokenSnapshotRecord

def main():
    df = pd.read_csv("scratch/resolved_tokens_72h.csv")
    df = df[df['status'] == 'RESOLVED'].copy()
    
    records = []
    for _, row in df.iterrows():
        d = row.to_dict()
        import math
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
        except Exception as e:
            pass
            
    scorer = OfflineScorer()
    scored_records = scorer.evaluate_all(records)
    
    # We want to specifically look at winners
    df_scored = pd.DataFrame([vars(r) for r in scored_records])
    winners = df_scored[df_scored['outcome_label'] == 'Winner']
    
    print(f"Total Winners found: {len(winners)}")
    
    # Let's categorize them by Mode
    def get_mode(row):
        mcap = row.get('t0_mcap_usd', 0)
        if 5000 <= mcap <= 30000: return 'Micro'
        if 30000 < mcap <= 100000: return 'DeathZone'
        if 100000 < mcap < 150000: return 'Gap'
        if 150000 <= mcap <= 500000: return 'Graduate'
        return 'Out of Bounds'
        
    winners['Mode'] = winners.apply(get_mode, axis=1)
    
    for mode in ['Micro', 'Graduate', 'DeathZone', 'Gap', 'Out of Bounds']:
        mode_winners = winners[winners['Mode'] == mode]
        if len(mode_winners) > 0:
            print(f"\n--- {mode} Winners ({len(mode_winners)}) ---")
            print(mode_winners['first_failed_gate'].value_counts(dropna=False))

if __name__ == "__main__":
    main()
