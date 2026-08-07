import argparse
import logging
from pathlib import Path

import asyncio

from src.data_puller.harvester import HistoricalHarvester
from src.evaluator.scorer import OfflineScorer
from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("LowMCSniper.Backtester")

def main():
    parser = argparse.ArgumentParser(description="Run the 14-Gate Backtest Pipeline")
    parser.add_argument("--harvest", type=int, default=0, help="Number of new tokens to harvest before backtesting. If 0, uses existing dataset.")
    parser.add_argument("--dataset", type=str, default="", help="Path to existing raw dataset JSON to use. If empty and harvest=0, uses the latest one.")
    args = parser.parse_args()

    dataset_path = None

    if args.harvest > 0:
        logger.info(f"Harvesting {args.harvest} new tokens...")
        # Will pull from a random 7-30 day window uniformly
        harvester = HistoricalHarvester()
        records = asyncio.run(harvester.harvest_historical_dataset(target_count=args.harvest))
        if not records:
            logger.error("Harvesting failed or returned no data.")
            return
        
        csv_path, json_path_str = harvester.export_dataset("raw_harvest")
        dataset_path = Path(json_path_str)
    elif args.dataset:
        dataset_path = Path(args.dataset)
        if not dataset_path.exists():
            logger.error(f"Dataset not found: {dataset_path}")
            return
    else:
        # Find the latest JSON in raw_data
        raw_files = list(settings.RAW_DATA_DIR.glob("*.json"))
        if not raw_files:
            logger.error(f"No raw datasets found in {settings.RAW_DATA_DIR}. Please run with --harvest N.")
            return
        dataset_path = max(raw_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Using most recent dataset: {dataset_path.name}")

    logger.info("=== Starting 14-Gate Backtest Calibration ===")
    
    scorer = OfflineScorer()
    try:
        records = scorer.load_dataset(dataset_path)
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return

    logger.info(f"Evaluating {len(records)} tokens...")
    scorer.evaluate_all(records)

    csv_out, json_out = scorer.export_scored_dataset()
    logger.info(f"Saved scored data to {csv_out}")
    
    report = scorer.generate_calibration_report()
    print("\n" + report)
    logger.info("Backtest evaluation complete.")

if __name__ == "__main__":
    main()
