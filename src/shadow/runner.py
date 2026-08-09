"""
Shadow Mode Runner module for real-time token discovery, T0 gate snapshotting,
and 24h outcome tracking on live DEX pool launches.
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import pandas as pd

from config.settings import settings
from src.data_puller.api_client import api_client

from src.shadow.telegram_bot import TelegramNotifier

logger = logging.getLogger("LowMCSniper.ShadowRunner")

SOLANA_BURN_ADDRESSES = {
    "11111111111111111111111111111111",
    "Incinerator11111111111111111111111111111111",
    "1111111111111111111111111111111111111111111",
}


RTL_CHARACTERS = {"\u202e", "\u202d", "\u202b", "\u202a", "\u200f", "\u200e", "\u2066", "\u2067", "\u2068", "\u2069"}


def has_rtl_control_chars(text: str) -> bool:
    """Detects Unicode Right-to-Left (RTL) override control characters used in scam tokens."""
    return any(char in RTL_CHARACTERS for char in text)


class ShadowRunner:
    """Orchestrates live discovery, real-time T0 gate snapshotting, and outcome resolution."""

    def __init__(
        self,
        network: str = "solana",
        storage_dir: Optional[Path] = None,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ):
        self.network = network
        self.storage_dir = storage_dir or (settings.BASE_DIR / "data" / "shadow")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.seen_pools_file = self.storage_dir / "seen_pools.json"
        self.pending_tokens_file = self.storage_dir / "pending_tokens.json"
        self.resolved_tokens_json = self.storage_dir / "resolved_tokens.json"
        self.resolved_tokens_csv = self.storage_dir / "resolved_tokens.csv"

        self.seen_pools: set[str] = self._load_seen_pools()
        self.pending_tokens: dict[str, dict[str, Any]] = self._load_pending_tokens()
        self.resolved_tokens: list[dict[str, Any]] = self._load_resolved_tokens()

        self.telegram = TelegramNotifier(bot_token=telegram_token, chat_id=telegram_chat_id)

    # --- Persistence Handlers ---

    def _load_seen_pools(self) -> set[str]:
        if self.seen_pools_file.exists():
            try:
                with open(self.seen_pools_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data)
            except Exception as e:
                logger.error(f"Error loading seen_pools.json: {e}")
        return set()

    def _save_seen_pools(self) -> None:
        try:
            with open(self.seen_pools_file, "w", encoding="utf-8") as f:
                json.dump(list(self.seen_pools), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving seen_pools.json: {e}")

    def _load_pending_tokens(self) -> dict[str, dict[str, Any]]:
        if self.pending_tokens_file.exists():
            try:
                with open(self.pending_tokens_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading pending_tokens.json: {e}")
        return {}

    def _save_pending_tokens(self) -> None:
        try:
            with open(self.pending_tokens_file, "w", encoding="utf-8") as f:
                json.dump(self.pending_tokens, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving pending_tokens.json: {e}")

    def _load_resolved_tokens(self) -> list[dict[str, Any]]:
        if self.resolved_tokens_json.exists():
            try:
                with open(self.resolved_tokens_json, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading resolved_tokens.json: {e}")
        return []

    def _save_resolved_tokens(self) -> None:
        try:
            with open(self.resolved_tokens_json, "w", encoding="utf-8") as f:
                json.dump(self.resolved_tokens, f, indent=2)
            
            if self.resolved_tokens:
                df = pd.DataFrame(self.resolved_tokens)
                df.to_csv(self.resolved_tokens_csv, index=False)
        except Exception as e:
            logger.error(f"Error saving resolved_tokens: {e}")

    # --- Discovery & Snapshot Logic ---

    async def discover_and_snapshot(self, pages: int = 2) -> int:
        """Polls GeckoTerminal new pools endpoint and captures T0 snapshots for fresh pools."""
        logger.info(f"Polling new pools for '{self.network}' (pages 1-{pages})...")
        new_count = 0

        for page in range(1, pages + 1):
            pools = await api_client.fetch_geckoterminal_new_pools(network=self.network, page=page)
            if not pools:
                continue

            for pool_data in pools:
                attributes = pool_data.get("attributes", {})
                pool_address = attributes.get("address")
                if not pool_address or pool_address in self.seen_pools:
                    continue

                # Extract token address from relationships or pool name
                relationships = pool_data.get("relationships", {})
                base_token_id = relationships.get("base_token", {}).get("data", {}).get("id", "")
                token_address = base_token_id.replace(f"{self.network}_", "") if base_token_id else ""
                
                name = attributes.get("name", "Unknown Pool")
                symbol = name.split("/")[0].strip() if "/" in name else name

                price_usd = float(attributes.get("base_token_price_usd") or 0.0)
                liquidity_usd = float(attributes.get("reserve_in_usd") or 0.0)
                mcap_usd = float(attributes.get("fdv_usd") or 0.0)
                
                volume_dict = attributes.get("volume_usd", {})
                vol_15m = float(volume_dict.get("m5", 0.0) or volume_dict.get("h1", 0.0) or 0.0)

                # --- Hygiene Filter 1: Unicode RTL Impersonation Scam Check ---
                has_rtl_scam = has_rtl_control_chars(name) or has_rtl_control_chars(symbol)
                if has_rtl_scam:
                    logger.warning(f"RTL Scam Character detected in symbol/name ({symbol}) for pool {pool_address}. Flagging.")

                # --- Hygiene Filter 2: Wide-Scope Collection Bounds ($5k-$500k MCap & >=$1k Liq) ---
                # Exclude uninitialized 0-block dust pools (<$5k MCap / <$1k Liq) and mega pools (>$500k MCap)
                # Raw records are preserved across the $5k-$500k spectrum for analysis-time gate testing
                if mcap_usd < 5000.0 or mcap_usd > 500000.0 or liquidity_usd < 1000.0:
                    logger.debug(f"Skipping out-of-scope pool: {symbol} (MCap: ${mcap_usd:,.0f}, Liq: ${liquidity_usd:,.0f})")
                    self.seen_pools.add(pool_address)
                    self._save_seen_pools()
                    continue

                logger.info(f"Discovered fresh pool: {symbol} ({pool_address}) | Price: ${price_usd:.6f} | Liq: ${liquidity_usd:,.0f} | MCap: ${mcap_usd:,.0f}")

                # Perform Real-Time T0 Gate Checks via On-Chain RPC
                snapshot = await self._capture_t0_snapshot(
                    pool_address=pool_address,
                    token_address=token_address,
                    symbol=symbol,
                    price_usd=price_usd,
                    liquidity_usd=liquidity_usd,
                    mcap_usd=mcap_usd,
                    vol_15m=vol_15m,
                    has_rtl_scam=has_rtl_scam,
                )

                self.seen_pools.add(pool_address)
                self.pending_tokens[pool_address] = snapshot
                new_count += 1

                self._save_seen_pools()
                self._save_pending_tokens()

                # Gentle pacing between RPC calls
                await asyncio.sleep(0.3)

        if new_count > 0:
            logger.info(f"Captured {new_count} new token T0 snapshots. Total pending: {len(self.pending_tokens)}")
        else:
            logger.info("No new pools found in this discovery pass.")

        return new_count

    async def _capture_t0_snapshot(
        self,
        pool_address: str,
        token_address: str,
        symbol: str,
        price_usd: float,
        liquidity_usd: float,
        mcap_usd: float,
        vol_15m: float,
        has_rtl_scam: bool = False,
    ) -> dict[str, Any]:
        """Runs immediate RPC calls for Gates 1, 4, 5, 9, 11a, 11b at launch moment (T0)."""
        t0_top10_pct = 15.0
        t0_dev_pct = 1.0
        t0_lp_locked_days = 0
        is_token_2022 = False
        has_malicious_ext = False

        if self.network == "solana" and token_address:
            # 1. Token-2022 & Extensions Check (Gate 11a/11b)
            token_info = await api_client.fetch_token_account_info(token_address)
            if token_info:
                owner = token_info.get("owner", "")
                if owner == "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb":
                    is_token_2022 = True
                    # Check base64 extensions
                    data_b64 = token_info.get("data", [""])[0]
                    if data_b64:
                        import base64
                        try:
                            raw_data = base64.b64decode(data_b64)
                            offset = 82
                            if len(raw_data) > offset:
                                offset += 1
                                while offset + 4 <= len(raw_data):
                                    ext_type = int.from_bytes(raw_data[offset:offset+2], "little")
                                    ext_len = int.from_bytes(raw_data[offset+2:offset+4], "little")
                                    if ext_type in (1, 10): # TransferFeeConfig or PermanentDelegate
                                        has_malicious_ext = True
                                    elif ext_type == 12: # DefaultAccountState
                                        if offset + 4 + 1 <= len(raw_data) and raw_data[offset+4] == 2:
                                            has_malicious_ext = True
                                    offset += 4 + ext_len
                        except Exception:
                            pass

            # 2. T0 Real-Time Holder & Dev Wallet Check (Gates 4 & 5)
            supply = await api_client.fetch_solana_token_supply(token_address)
            accounts = await api_client.fetch_solana_token_largest_accounts(token_address)

            if supply and accounts and supply > 0:
                ex_burn_accounts = [acc for acc in accounts if acc["address"] not in SOLANA_BURN_ADDRESSES]
                top10_sum = sum(acc["uiAmount"] for acc in ex_burn_accounts[:10])
                t0_top10_pct = round((top10_sum / supply) * 100.0, 2)

                # Exclude the AMM Bonding Curve Vault (#1 account if holding >40% supply) from Dev Wallet
                non_pool_accounts = ex_burn_accounts
                if ex_burn_accounts and (ex_burn_accounts[0]["uiAmount"] / supply) > 0.40:
                    non_pool_accounts = ex_burn_accounts[1:]

                if non_pool_accounts:
                    t0_dev_pct = round((non_pool_accounts[0]["uiAmount"] / supply) * 100.0, 2)
                else:
                    t0_dev_pct = 0.0

            # 3. Real-Time LP Lock/Burn Check (Gate 1)
            lp_mint = await api_client.fetch_pool_lp_mint(pool_address)
            if lp_mint == "PROGRAM_LOCKED":
                t0_lp_locked_days = 365
            elif lp_mint:
                lp_supply = await api_client.fetch_solana_token_supply(lp_mint)
                lp_accounts = await api_client.fetch_solana_token_largest_accounts(lp_mint)
                if lp_supply and lp_accounts and lp_supply > 0:
                    for acc in lp_accounts[:3]:
                        if acc["address"] in SOLANA_BURN_ADDRESSES and (acc["uiAmount"] / lp_supply) >= 0.80:
                            t0_lp_locked_days = 365
                            break

        liq_mcap_ratio = round(liquidity_usd / mcap_usd, 4) if mcap_usd > 0 else 0.0

        short_addr = f" ({token_address[:5]}...)" if token_address and len(token_address) >= 5 else ""
        display_symbol = f"{symbol}{short_addr}"

        return {
            "pool_address": pool_address,
            "token_address": token_address,
            "symbol": display_symbol,
            "raw_symbol": symbol,
            "network": self.network,
            "t0_timestamp": int(time.time()),
            "t0_date": datetime.now(timezone.utc).isoformat(),
            "t0_price_usd": price_usd,
            "t0_liquidity_usd": liquidity_usd,
            "t0_mcap_usd": mcap_usd,
            "t0_volume_usd_15m": vol_15m,
            "t0_top10_holder_pct": t0_top10_pct,
            "t0_dev_wallet_pct": t0_dev_pct,
            "t0_lp_locked_days": t0_lp_locked_days,
            "t0_is_token_2022": is_token_2022,
            "t0_has_malicious_extensions": has_malicious_ext,
            "t0_has_rtl_scam": has_rtl_scam,
            "liq_mcap_ratio": liq_mcap_ratio,
            "status": "PENDING",
        }

    # --- Outcome Resolution ---

    async def evaluate_matured_tokens(self, eval_delay_seconds: int = 86400) -> int:
        """Evaluates pending tokens that have reached their outcome check time (24h or test threshold)."""
        now = int(time.time())
        matured_keys = [
            k for k, v in self.pending_tokens.items()
            if now - v["t0_timestamp"] >= eval_delay_seconds
        ]

        if not matured_keys:
            logger.info(f"No pending tokens have reached maturity delay ({eval_delay_seconds}s). Pending queue size: {len(self.pending_tokens)}")
            return 0

        logger.info(f"Evaluating {len(matured_keys)} matured tokens for final 24h ROI outcomes...")
        resolved_count = 0

        for pool_address in matured_keys:
            snapshot = self.pending_tokens[pool_address]
            token_address = snapshot.get("token_address", "")
            t0_price = snapshot.get("t0_price_usd", 0.0)

            tfinal_price = 0.0
            tfinal_vol_24h = 0.0
            tfinal_liq = 0.0

            # Try GeckoTerminal pool state first
            pool_data = await api_client.fetch_geckoterminal_pool(self.network, pool_address)
            if pool_data:
                attr = pool_data.get("attributes", {})
                tfinal_price = float(attr.get("base_token_price_usd") or 0.0)
                tfinal_liq = float(attr.get("reserve_in_usd") or 0.0)
                tfinal_vol_24h = float(attr.get("volume_usd", {}).get("h24", 0.0) or 0.0)

            # Liquidity Collapse Check: Drained/rugged pools returning price artifacts on zero reserves
            is_liquidity_drained = (tfinal_liq < 500.0) or (t0_liq > 0 and (tfinal_liq / t0_liq) < 0.05)

            # Fallback to OHLCV candles if pool state returns 0 AND liquidity is not drained
            if tfinal_price <= 0 and not is_liquidity_drained:
                ohlcv = await api_client.fetch_geckoterminal_ohlcv(self.network, pool_address, resolution="hour")
                if ohlcv:
                    ohlcv.sort(key=lambda c: c[0])
                    tfinal_price = float(ohlcv[-1][4])
                    tfinal_vol_24h = sum(float(c[5]) for c in ohlcv)

            if is_liquidity_drained:
                tfinal_price = 0.0
                roi = 0.0
            else:
                roi = round(tfinal_price / t0_price, 4) if t0_price > 0 else 0.0

            # Calculate evaluation window label dynamically
            if eval_delay_seconds >= 3600:
                win_str = f"{round(eval_delay_seconds / 3600, 1)}h"
            else:
                win_str = f"{round(eval_delay_seconds / 60)}m"

            # Outcome Classification
            if roi >= 2.0:
                label = "Winner"
                reason = f"{win_str} ROI was {roi:.2f}x"
            elif roi <= 0.2:
                label = "Rug / dead"
                reason = f"{win_str} ROI plummeted to {roi:.2f}x"
            else:
                label = "Flat / mediocre"
                reason = f"Survived but {win_str} ROI only {roi:.2f}x"

            snapshot.update({
                "tfinal_timestamp": now,
                "tfinal_date": datetime.now(timezone.utc).isoformat(),
                "tfinal_24h_price_usd": tfinal_price,
                "tfinal_24h_vol_usd": tfinal_vol_24h,
                "roi_24h": roi,
                "outcome_label": label,
                "outcome_reason": reason,
                "status": "RESOLVED",
            })

            self.resolved_tokens.append(snapshot)
            del self.pending_tokens[pool_address]
            resolved_count += 1

            self._save_pending_tokens()
            self._save_resolved_tokens()

            logger.info(f"Resolved {snapshot.get('symbol')} ({pool_address}): ROI {roi:.2f}x -> {label}")
            await asyncio.sleep(1.5)

        logger.info(f"Successfully resolved {resolved_count} tokens. Total resolved: {len(self.resolved_tokens)}")
        return resolved_count

    # --- Live Calibration Report ---

    def generate_report(self) -> str:
        """Generates a human-readable summary of the shadow runner performance and gate accuracy."""
        lines = []
        lines.append("=" * 65)
        lines.append("SHADOW MODE RUNNER — LIVE CALIBRATION REPORT")
        lines.append("=" * 65)
        lines.append(f"Network: {self.network.upper()} | Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"Total Pools Discovered: {len(self.seen_pools)}")
        lines.append(f"Tokens Pending 24h Outcome: {len(self.pending_tokens)}")
        lines.append(f"Tokens Fully Resolved: {len(self.resolved_tokens)}")
        lines.append("")

        if not self.resolved_tokens:
            lines.append("No resolved tokens yet. Keep the shadow runner running to capture 24h outcomes!")
            lines.append("=" * 65)
            return "\n".join(lines)

        df = pd.DataFrame(self.resolved_tokens)
        lines.append("=== OUTCOME DISTRIBUTION ===")
        for label, count in df["outcome_label"].value_counts().items():
            pct = count / len(df) * 100.0
            lines.append(f"  {label}: {count} ({pct:.1f}%)")
        lines.append("")

        lines.append("=== GATE PERFORMANCE CROSS-TABULATION (REAL T0 DATA) ===")
        
        # Gate 1: LP Lock
        lines.append("--- Gate 1: LP Lock/Burn (>= 30 days) ---")
        for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
            sub = df[df["outcome_label"] == label]
            if len(sub) > 0:
                pass_cnt = (sub["t0_lp_locked_days"] >= 30).sum()
                lines.append(f"  {label} ({len(sub)}): {pass_cnt}/{len(sub)} pass ({pass_cnt/len(sub)*100:.1f}%)")
        lines.append("")

        # Gate 4: Top 10 Holder %
        lines.append("--- Gate 4: Top 10 Holder % (<= 20%) ---")
        for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
            sub = df[df["outcome_label"] == label]
            if len(sub) > 0:
                pass_cnt = (sub["t0_top10_holder_pct"] <= 20).sum()
                mean_val = sub["t0_top10_holder_pct"].mean()
                lines.append(f"  {label} ({len(sub)}): {pass_cnt}/{len(sub)} pass (mean: {mean_val:.1f}%)")
        lines.append("")

        # Gate 5: Dev Wallet %
        lines.append("--- Gate 5: Dev Wallet % (<= 3%) ---")
        for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
            sub = df[df["outcome_label"] == label]
            if len(sub) > 0:
                pass_cnt = (sub["t0_dev_wallet_pct"] <= 3).sum()
                mean_val = sub["t0_dev_wallet_pct"].mean()
                lines.append(f"  {label} ({len(sub)}): {pass_cnt}/{len(sub)} pass (mean: {mean_val:.1f}%)")
        lines.append("")

        # Gate 9: Liq/MCap Ratio
        lines.append("--- Gate 9: Liq/MCap Ratio (>= 0.25) ---")
        for label in ["Winner", "Flat / mediocre", "Rug / dead"]:
            sub = df[df["outcome_label"] == label]
            if len(sub) > 0:
                pass_cnt = (sub["liq_mcap_ratio"] >= 0.25).sum()
                mean_val = sub["liq_mcap_ratio"].mean()
                lines.append(f"  {label} ({len(sub)}): {pass_cnt}/{len(sub)} pass (mean: {mean_val:.3f})")
        lines.append("")

        lines.append("=" * 65)
        return "\n".join(lines)

    # --- Main Execution Loop ---

    async def run_loop(
        self,
        poll_interval: int = 30,
        eval_delay_seconds: int = 86400,
        max_iterations: Optional[int] = None,
    ) -> None:
        """Main continuous monitor loop for live VPS or background local running."""
        logger.info(f"Starting Shadow Runner loop for network '{self.network}'...")
        logger.info(f"Poll Interval: {poll_interval}s | Evaluation Delay: {eval_delay_seconds}s ({eval_delay_seconds/3600:.1f}h)")

        # Send Telegram Startup Alert
        await self.telegram.send_startup_notification(self.network)

        # Start background Telegram update listener (for buttons & /getdata commands)
        listener_task = asyncio.create_task(self.telegram.poll_listener_loop(self))

        last_heartbeat_time = time.time()
        iteration = 0
        try:
            while True:
                iteration += 1
                logger.info(f"\n--- Shadow Pass #{iteration} ---")
                
                # 1. Discover fresh pools & take T0 snapshot
                try:
                    await self.discover_and_snapshot(pages=2)
                except Exception as e:
                    logger.error(f"Error during discovery pass: {e}")

                # 2. Check for matured tokens & compute ROI outcomes
                try:
                    await self.evaluate_matured_tokens(eval_delay_seconds=eval_delay_seconds)
                except Exception as e:
                    logger.error(f"Error during outcome evaluation: {e}")

                # 3. Hourly Telegram Heartbeat (Every 3600 seconds)
                now = time.time()
                if now - last_heartbeat_time >= 3600:
                    report = self.generate_report()
                    await self.telegram.send_hourly_heartbeat(
                        pending_count=len(self.pending_tokens),
                        resolved_count=len(self.resolved_tokens),
                        report_text=report,
                    )
                    last_heartbeat_time = now

                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Reached max iterations ({max_iterations}). Stopping loop.")
                    break

                logger.info(f"Sleeping for {poll_interval} seconds before next pass...")
                await asyncio.sleep(poll_interval)
        finally:
            listener_task.cancel()
            await api_client.close()
            logger.info("Shadow Runner loop terminated gracefully.")
