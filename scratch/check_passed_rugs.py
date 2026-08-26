import pandas as pd
from src.evaluator.scorer import OfflineScorer
from src.data_puller.harvester import TokenSnapshotRecord
import math

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
    except Exception as e:
        pass

scorer = OfflineScorer()
scored_records = scorer.evaluate_all(records)

passed_rugs = [r for r in scored_records if r.passed_all_gates and r.outcome_label == 'Rug / dead']

print(f"Total passed rugs: {len(passed_rugs)}")
for r in passed_rugs[:15]:
    print(f"{r.symbol} - Gate 4 (Top 10): {r.t0_top10_holder_pct:.2f}% | Gate 5 (Dev): {r.t0_dev_wallet_pct:.2f}%")
