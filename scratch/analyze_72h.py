import pandas as pd
from pathlib import Path
from src.evaluator.scorer import OfflineScorer
from src.data_puller.harvester import TokenSnapshotRecord

def main():
    df = pd.read_csv("scratch/resolved_tokens_72h.csv")
    
    # Filter out DROPPED tokens if we only want RESOLVED
    df = df[df['status'] == 'RESOLVED'].copy()
    
    # Prepare records for Pydantic
    records = []
    for _, row in df.iterrows():
        d = row.to_dict()
        
        # Handle nan values for pydantic
        import math
        for k, v in d.items():
            if isinstance(v, float) and math.isnan(v):
                d[k] = None
                
        # Scorer needs 't0_holder_count' if exact/floor are used
        exact = d.get('t0_holder_count_exact')
        floor = d.get('t0_holder_count_floor')
        if exact is not None and not pd.isna(exact):
            d['t0_holder_count'] = int(exact)
        elif floor is not None and not pd.isna(floor):
            d['t0_holder_count'] = int(floor)
        else:
            d['t0_holder_count'] = 0
            
        # Pydantic requires some fields to be present.
        # Add 'chain' and 'name' which might be missing but required by schema
        if 'chain' not in d or d['chain'] is None:
            d['chain'] = d.get('network', 'solana')
        if 'name' not in d or d['name'] is None:
            d['name'] = d.get('symbol', 'Unknown')
        if 'created_at_utc' not in d or d['created_at_utc'] is None:
            d['created_at_utc'] = d.get('t0_date', '')
            
        # Make sure t0_forensics_collected parses as boolean. CSV has "False" string potentially.
        fc = d.get('t0_forensics_collected')
        if isinstance(fc, str):
            d['t0_forensics_collected'] = fc.lower() == 'true'
            
        try:
            record = TokenSnapshotRecord(**d)
            records.append(record)
        except Exception as e:
            print(f"Error parsing record {d.get('pool_address')}: {e}")
            
    print(f"Loaded {len(records)} valid RESOLVED records.")
    
    scorer = OfflineScorer()
    scored_records = scorer.evaluate_all(records)
    
    report = scorer.generate_calibration_report()
    
    with open("scratch/72h_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
        
    print(report)

if __name__ == "__main__":
    main()
