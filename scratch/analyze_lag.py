import pandas as pd
import numpy as np

def run_analysis():
    df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (7).csv")
    df_resolved = df[df['status'] == 'RESOLVED'].copy()
    
    total_resolved = len(df_resolved)
    winners = df_resolved[df_resolved['outcome_label'] == 'Winner']
    
    print("="*60)
    print(" HELIUS DAS T0 HOLDER COUNT ANALYSIS (48H DATA)")
    print("="*60)
    print(f"Total Resolved Tokens: {total_resolved}")
    print(f"Total Winners: {len(winners)}")
    
    # Let's check how many were capped vs exact
    capped = winners['t0_holder_count_capped'].sum()
    exact = len(winners) - capped
    
    print(f"\nWinners Capped at >= 100 holders: {capped}")
    print(f"Winners with Exact Holders (< 100): {exact}")
    
    if exact > 0:
        print("\n--- Distribution of Exact Holder Counts for Winners ---")
        exact_series = winners[winners['t0_holder_count_capped'] == False]['t0_holder_count_exact']
        print(exact_series.describe())
        print("\nValue Counts (Lowest 10):")
        print(exact_series.value_counts().sort_index().head(10))

if __name__ == "__main__":
    run_analysis()
