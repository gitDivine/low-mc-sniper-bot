import pandas as pd
import sys

def generate_report(csv_path):
    df = pd.read_csv(csv_path)
    if len(df) == 0:
        return "No resolved tokens in CSV."
        
    lines = []
    lines.append("=== BATCH 2: CLEANED ORGANICS ANALYSIS ===")
    
    # Apply baseline anti-scam filter to identify true organics vs wash-traded scams
    df['is_organic'] = (df['t0_top10_holder_pct'] <= 50.0) & (df['t0_dev_wallet_pct'] <= 20.0)
    
    organics = df[df['is_organic']]
    scams = df[~df['is_organic']]
    
    lines.append(f"Total Tokens: {len(df)}")
    lines.append(f"Organic Tokens (Dev<=20%, Top10<=50%): {len(organics)}")
    lines.append(f"Obvious Scams (Dev>20% or Top10>50%): {len(scams)}")
    lines.append("")
    
    lines.append("--- OUTCOMES FOR ORGANICS ---")
    org_labels = organics['outcome_label'].value_counts()
    for label, count in org_labels.items():
        lines.append(f"  {label}: {count} ({count/len(organics)*100:.1f}%)")
    lines.append("")
    
    org_winners = organics[organics['outcome_label'] == 'Winner']
    lines.append(f"--- ORGANIC WINNERS ({len(org_winners)}) DETAILS ---")
    
    if len(org_winners) > 0:
        for _, row in org_winners.iterrows():
            lines.append(f"{row['symbol']}: ROI {row['roi_24h']:.2f}x, Top10 {row['t0_top10_holder_pct']}%, Dev {row['t0_dev_wallet_pct']}%, Liq/MCap {row['liq_mcap_ratio']:.3f}, T0 Liq {row['t0_liquidity_usd']}")
        
        lines.append("")
        lines.append("--- ORGANIC WINNERS STATS ---")
        lines.append(f"Top 10 Holder %  | Min: {org_winners['t0_top10_holder_pct'].min():.2f}%, Max: {org_winners['t0_top10_holder_pct'].max():.2f}%, Mean: {org_winners['t0_top10_holder_pct'].mean():.2f}%")
        lines.append(f"Dev Wallet %     | Min: {org_winners['t0_dev_wallet_pct'].min():.2f}%, Max: {org_winners['t0_dev_wallet_pct'].max():.2f}%, Mean: {org_winners['t0_dev_wallet_pct'].mean():.2f}%")
        lines.append(f"Liq/MCap Ratio   | Min: {org_winners['liq_mcap_ratio'].min():.3f}, Max: {org_winners['liq_mcap_ratio'].max():.3f}, Mean: {org_winners['liq_mcap_ratio'].mean():.3f}")
    
    return '\n'.join(lines)

if __name__ == "__main__":
    csv_path = sys.argv[1]
    out_path = sys.argv[2]
    report = generate_report(csv_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("Done")
