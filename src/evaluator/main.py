"""CLI entry point for running Script 2 (Offline 14-Gate Evaluator & Calibrator)."""
import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config.settings import settings
from src.evaluator.scorer import OfflineScorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("LowMCSniper.ScorerCLI")


def find_latest_dataset() -> Path:
    """Locate the most recent harvested JSON or CSV file in data/raw/."""
    raw_dir = settings.RAW_DATA_DIR
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_dir}")

    files = sorted(list(raw_dir.glob("*.json")) + list(raw_dir.glob("*.csv")), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No harvested datasets found in {raw_dir}. Run Script 1 first!")
    return files[0]


def main() -> None:
    """Parse CLI arguments and execute offline scoring."""
    parser = argparse.ArgumentParser(description="Low-MC Token Sniper Bot — Offline 14-Gate Evaluator (Script 2)")
    parser.add_argument("--file", type=str, default=None, help="Path to raw harvested dataset (default: latest in data/raw/)")
    
    args = parser.parse_args()
    
    try:
        if args.file:
            dataset_path = Path(args.file)
        else:
            dataset_path = find_latest_dataset()

        logger.info(f"=== Starting Low-MC Token Sniper Bot Evaluator (Script 2) ===")
        logger.info(f"Target Dataset: {dataset_path}")

        scorer = OfflineScorer()
        records = scorer.load_dataset(dataset_path)
        scorer.evaluate_all(records)

        # Print report to console
        report = scorer.generate_calibration_report()
        print("\n" + report + "\n")

        # Export scored artifacts
        csv_path, json_path = scorer.export_scored_dataset()
        logger.info(f"=== Scoring Complete. Scored dataset saved to {csv_path} ===")

    except Exception as e:
        logger.exception(f"Fatal error during scoring evaluation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
