import pandas as pd

df = pd.read_csv(r"C:\Users\njoku\Downloads\resolved_tokens (3).csv")

target_addrs = [
    "6m9ux7VfoxgnhvDyFczGiLkXf7yehYNZm1Ky3Y9vigeb",
    "3YUR6fezkKGAANi65Uqff9PUVVGJeCT1LGYQzeU1BAGS",
    "EQE9sprZb9kFMaTa89DRmKAV4BEHKd55WZkPyWGBpump",
    "DHFSEDzTj7o51Ar8RAD5tS76dcmLU9r7Qpyyhhr2ccKZ",
    "2UCET17KNDp9VKaquptbc3WrNHsEhTWJBbwqJjPxQapt"
]

print("=" * 75)
print("DEEP RAW DATASET INTEGRITY AUDIT")
print("=" * 75)

for addr in target_addrs:
    sub = df[(df["token_address"] == addr) | (df["pool_address"] == addr)]
    print(f"\nSearching for Address: {addr}")
    print(f"  Matching Rows Found: {len(sub)}")
    for idx, row in sub.iterrows():
        print(f"   Index #{idx}: Symbol='{row['symbol']}' | TokenAddr='{row['token_address']}' | PoolAddr='{row['pool_address']}'")
        print(f"              T0 Price=${row['t0_price_usd']:.8f} | TFinal Price=${row['tfinal_24h_price_usd']:.8f} | ROI={row['roi_24h']}x")
        print(f"              T0 Date={row['t0_date']} | TFinal Date={row['tfinal_date']}")

print("=" * 75)
