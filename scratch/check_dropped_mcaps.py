import pandas as pd
import re

df = pd.read_csv('scratch/resolved_tokens_48h.csv')
dropped = df[df['status'] == 'DROPPED']

mcaps = []
liqs = []
for r in dropped['outcome_reason']:
    if pd.isna(r): continue
    m = re.search(r'MCap: \$([0-9,\.]+), Liq: \$([0-9,\.]+)', str(r))
    if m:
        mcaps.append(float(m.group(1).replace(',','')))
        liqs.append(float(m.group(2).replace(',','')))

print(f'Total parsed: {len(mcaps)}')
print(f'Below 5k: {sum(m < 5000 for m in mcaps)}')
print(f'Above 500k: {sum(m > 500000 for m in mcaps)}')
print(f'Liq under 1k (but mcap 5k-500k): {sum(5000 <= m <= 500000 and l < 1000 for m, l in zip(mcaps, liqs))}')
