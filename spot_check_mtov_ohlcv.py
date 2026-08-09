import asyncio
from src.data_puller.api_client import api_client

async def main():
    pool_address = "GGRPtxSE4KBkanWS1ukytJiBgJ3nNStn8GzRz9vXL4A"
    
    print("=" * 70)
    print("OHLCV SPOT CHECK FOR MTOV POOL")
    print("=" * 70)
    
    ohlcv = await api_client.fetch_geckoterminal_ohlcv("solana", pool_address, resolution="hour")
    print(f"OHLCV Length: {len(ohlcv) if ohlcv else 0}")
    if ohlcv:
        print("First Candle:", ohlcv[0])
        print("Last Candle :", ohlcv[-1])

if __name__ == "__main__":
    asyncio.run(main())
