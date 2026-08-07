import asyncio
import logging
from src.data_puller.harvester import HistoricalHarvester

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

async def main():
    harvester = HistoricalHarvester(target_chain="solana")
    try:
        await harvester.harvest_historical_dataset(target_count=150)
    except Exception as e:
        logging.error(f"Harvest interrupted: {e}")
    finally:
        harvester.export_dataset()

if __name__ == "__main__":
    asyncio.run(main())
