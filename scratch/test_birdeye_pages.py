import asyncio
import json
from src.data_puller.api_client import api_client

async def main():
    swaps = await api_client.fetch_birdeye_swaps('ASpbtWALGUicfkpym4UA3CZdy1QehsoA3rLTd3uuVzzS', max_pages=3)
    print(f'Total swaps: {len(swaps)}')
    if swaps:
        print(f'First swap time (index 0): {swaps[0]["blockUnixTime"]}')
        print(f'Last swap time (index {len(swaps)-1}): {swaps[-1]["blockUnixTime"]}')
    await api_client.close()

if __name__ == "__main__":
    asyncio.run(main())
