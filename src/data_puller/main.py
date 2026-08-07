"""CLI entry point for running Script 1 (Historical Data Harvester)."""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Fix Windows cp1252 console encoding issues
if sys.stdout.encoding.lower() == "cp1252":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config.settings import settings
from src.data_puller.api_client import api_client
from src.data_puller.harvester import HistoricalHarvester

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("LowMCSniper.HarvesterCLI")


async def async_main(args: argparse.Namespace) -> None:
    """Async execution flow for harvesting historical pair data across target chains."""
    logger.info("=== Starting Low-MC Token Sniper Bot Harvester (Script 1) ===")
    
    chains_to_run = ["solana", "bsc", "arbitrum"] if args.chain == "all" else [args.chain]
    logger.info(f"Target Chains: {chains_to_run} | Target Count per Chain: {args.count}")

    try:
        for chain in chains_to_run:
            logger.info(f"\n--- Starting Harvest for Chain: {chain.upper()} ---")
            harvester = HistoricalHarvester(target_chain=chain)
            await harvester.harvest_historical_dataset(target_count=args.count)
            
            if harvester.records:
                csv_path, json_path = harvester.export_dataset()
                logger.info(f"=== {chain.upper()} Harvest Complete. Saved {len(harvester.records)} records to {csv_path} ===")
            else:
                logger.warning(f"No candidate records harvested for '{chain}'.")

    finally:
        await api_client.close()
        logger.info("HTTP client closed gracefully.")


def main() -> None:
    """Parse CLI arguments and run async main."""
    parser = argparse.ArgumentParser(description="Low-MC Token Sniper Bot — Historical Data Harvester (Script 1)")
    parser.add_argument("--chain", type=str, choices=["solana", "bsc", "arbitrum", "all"], default="solana", help="Target blockchain or 'all' (default: solana)")
    parser.add_argument("--count", type=int, default=150, help="Target number of historical token records per chain (default: 150)")
    
    args = parser.parse_args()
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logger.warning("Harvester interrupted by user (Ctrl+C). Exiting.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error during harvesting: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
