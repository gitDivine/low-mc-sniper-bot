import pandas as pd
from src.evaluator.scorer import OfflineScorer
from src.data_puller.harvester import TokenSnapshotRecord

def main():
    print("Loading 48-hour data...")
    df = pd.read_csv("scratch/resolved_tokens_48h.csv")
    df = df[df['status'] == 'RESOLVED'].copy()
    print(f"Total resolved tokens loaded: {len(df)}")
    
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
    
    print("\n" + "="*80)
    print(" 48H CALIBRATION REPORT ")
    print("="*80)
    report = scorer.generate_calibration_report()
    print(report)

if __name__ == "__main__":
    main()
