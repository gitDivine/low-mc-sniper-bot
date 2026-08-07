"""CLI entry point for running the Low-MC Token Sniper Bot Shadow Mode Runner."""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Fix Windows cp1252 console encoding issues
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.shadow.runner import ShadowRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("LowMCSniper.ShadowCLI")


async def async_main(args: argparse.Namespace) -> None:
    eval_delay_sec = args.eval_delay_minutes * 60

    if args.test_mode:
        logger.info("=== TEST-MODE ENABLED: Setting evaluation delay to 5 minutes & poll interval to 15s ===")
        eval_delay_sec = 300 # 5 minutes
        args.poll_interval = 15

    runner = ShadowRunner(
        network=args.network,
        telegram_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat_id,
    )

    if args.report:
        print("\n" + runner.generate_report() + "\n")
        return

    if args.once:
        logger.info("=== Executing Single Discovery & Evaluation Pass (--once) ===")
        await runner.discover_and_snapshot(pages=args.pages)
        await runner.evaluate_matured_tokens(eval_delay_seconds=eval_delay_sec)
        print("\n" + runner.generate_report() + "\n")
        return

    # Continuous loop mode
    logger.info(f"=== Starting Shadow Mode Runner (Network: {args.network.upper()}) ===")
    await runner.run_loop(
        poll_interval=args.poll_interval,
        eval_delay_seconds=eval_delay_sec,
        max_iterations=args.iterations,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Low-MC Token Sniper Bot — Shadow Mode Runner")
    parser.add_argument("--network", type=str, default="solana", help="Target blockchain (default: solana)")
    parser.add_argument("--poll-interval", type=int, default=30, help="Seconds between discovery polls (default: 30)")
    parser.add_argument("--eval-delay-minutes", type=int, default=1440, help="Minutes to wait before evaluating 24h ROI outcomes (default: 1440 = 24 hours)")
    parser.add_argument("--pages", type=int, default=2, help="GeckoTerminal pages to poll per pass (default: 2)")
    parser.add_argument("--once", action="store_true", help="Run a single discovery + evaluation pass and exit")
    parser.add_argument("--test-mode", action="store_true", help="Fast-test mode: 5-minute outcome delay, 15s poll interval")
    parser.add_argument("--report", action="store_true", help="Generate and print live calibration report from disk then exit")
    parser.add_argument("--iterations", type=int, default=None, help="Optional max iterations before exiting loop")
    parser.add_argument("--telegram-token", type=str, default=None, help="Optional Telegram Bot Token for alerts & CSV retrieval")
    parser.add_argument("--telegram-chat-id", type=str, default=None, help="Optional Telegram Chat ID for alerts & CSV retrieval")

    args = parser.parse_args()

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logger.warning("Shadow Runner interrupted by user (Ctrl+C). Exiting.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error in Shadow Runner: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
