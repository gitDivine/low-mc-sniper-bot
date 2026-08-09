import asyncio
from src.data_puller.api_client import api_client

async def main():
    pool_address = "GGRPtxSE4KBkanWS1ukytJiBgJ3nNStn8GzRz9vXL4A"
    token_address = "J6LSivR3nt1LajG9TLaf8mvaGduSe6x4QXrsRDt1gsDz"
    
    print("=" * 70)
    print("SPOT CHECK: MTOV ON-CHAIN / GECKOTERMINAL PRICE DATA")
    print("=" * 70)
    
    pool_data = await api_client.fetch_geckoterminal_pool("solana", pool_address)
    print("Pool Data from GeckoTerminal:")
    if pool_data:
        attr = pool_data.get("data", {}).get("attributes", {})
        print(f"  Name                    : {attr.get('name')}")
        print(f"  Base Token Price (USD)  : ${attr.get('base_token_price_usd')}")
        print(f"  Reserve in USD          : ${attr.get('reserve_in_usd')}")
        print(f"  FDV in USD              : ${attr.get('fdv_usd')}")
        print(f"  Price Change 24h        : {attr.get('price_change_percentage', {})}")
    else:
        print("  Could not fetch pool data")

if __name__ == "__main__":
    asyncio.run(main())
