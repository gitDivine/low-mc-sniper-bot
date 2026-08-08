import pandas as pd

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (2).csv")

df["time_delta_sec"] = df["tfinal_timestamp"] - df["t0_timestamp"]
df["time_delta_hours"] = df["time_delta_sec"] / 3600.0

print("=" * 65)
print("TIMESTAMP DELTA AUDIT (VERIFYING TRUE 24H RESOLUTION)")
print("=" * 65)
print(f"Total Rows: {len(df)}")
print(f"Min Time Delta  : {df['time_delta_hours'].min():.2f} hours ({df['time_delta_sec'].min()} seconds)")
print(f"Max Time Delta  : {df['time_delta_hours'].max():.2f} hours ({df['time_delta_sec'].max()} seconds)")
print(f"Mean Time Delta : {df['time_delta_hours'].mean():.2f} hours")
print(f"Median Time Delta: {df['time_delta_hours'].median():.2f} hours")
print("\nSample Rows with Time Deltas:")
for idx, row in df.head(10).iterrows():
    print(f"  Symbol: {row['symbol']:<10} | T0: {row['t0_date'][:19]} | TFinal: {row['tfinal_date'][:19]} | Delta: {row['time_delta_hours']:.2f}h")
print("=" * 65)
