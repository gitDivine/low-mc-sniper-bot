import pandas as pd
import glob
import asyncio
from src.data_puller.api_client import api_client

async def check_insane_rois():
    files = glob.glob('C:/Users/njoku/Downloads/resolved_tokens*.csv')
    high_roi_pools = []
    
    for csv_file in files:
        try:
            df = pd.read_csv(csv_file)
            for _, row in df.iterrows():
                if row.get('roi_24h', 0) > 10000:
                    high_roi_pools.append({
                        'symbol': row.get('symbol'),
                        'pool': row.get('pool_address'),
                        'roi': row.get('roi_24h'),
                        't0_price': row.get('t0_price_usd')
                    })
        except:
            pass
            
    print(f"Found {len(high_roi_pools)} pools with ROI > 10000")
    
    for pool in high_roi_pools:
        print(f"\nToken: {pool['symbol']} | Pool: {pool['pool']} | Recorded ROI: {pool['roi']}")
        pool_data = await api_client.fetch_geckoterminal_pool('solana', pool['pool'])
        if pool_data:
            attr = pool_data.get('attributes', {})
            tfinal_price = float(attr.get('base_token_price_usd') or 0.0)
            tfinal_liq = float(attr.get('reserve_in_usd') or 0.0)
            print(f"  Live Price: {tfinal_price}")
            print(f"  Live Liquidity: {tfinal_liq}")
            print(f"  Calculated Live ROI: {tfinal_price / pool['t0_price'] if pool['t0_price'] > 0 else 0}")
        else:
            print("  GeckoTerminal returned no data for this pool.")

    await api_client.close()

if __name__ == "__main__":
    asyncio.run(check_insane_rois())
