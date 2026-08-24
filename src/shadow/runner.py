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
        self.waiting_t0_file = self.storage_dir / "waiting_t0.json"

        self.seen_pools: set[str] = self._load_seen_pools()
        self.pending_tokens: dict[str, dict[str, Any]] = self._load_pending_tokens()
        self.resolved_tokens: list[dict[str, Any]] = self._load_resolved_tokens()
        self.waiting_t0_tokens: dict[str, dict[str, Any]] = self._load_waiting_t0_tokens()

        self.telegram = TelegramNotifier(bot_token=telegram_token, chat_id=telegram_chat_id)

    # --- Persistence Handlers ---

    def _load_waiting_t0_tokens(self) -> dict[str, dict[str, Any]]:
        if self.waiting_t0_file.exists():
            try:
                with open(self.waiting_t0_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading waiting_t0.json: {e}")
        return {}

    def _save_waiting_t0_tokens(self) -> None:
        try:
            with open(self.waiting_t0_file, "w", encoding="utf-8") as f:
                json.dump(self.waiting_t0_tokens, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving waiting_t0.json: {e}")

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
                
                # Calculate age_hours from pool_created_at
                pool_created_at_str = attributes.get("pool_created_at")
                age_hours = 0.5  # default if missing
                if pool_created_at_str:
                    try:
                        from datetime import datetime, timezone
                        pool_dt = datetime.fromisoformat(pool_created_at_str.replace('Z', '+00:00'))
                        age_hours = (datetime.now(timezone.utc) - pool_dt).total_seconds() / 3600.0
                    except Exception as e:
                        logger.warning(f"Failed to parse pool_created_at '{pool_created_at_str}': {e}")

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

                logger.info(f"Discovered fresh pool: {symbol} ({pool_address}) | Queuing for 15m maturity...")
                
                self.waiting_t0_tokens[pool_address] = {
                    "pool_address": pool_address,
                    "token_address": token_address,
                    "symbol": symbol,
                    "pool_created_at": pool_created_at_str,
                    "has_rtl_scam": has_rtl_scam,
                    "discovery_time": time.time(),
                }
                
                self.seen_pools.add(pool_address)
                new_count += 1

                self._save_seen_pools()
                self._save_waiting_t0_tokens()

                # Gentle pacing between RPC calls
                await asyncio.sleep(0.3)

        if new_count > 0:
            logger.info(f"Discovered {new_count} fresh pools. Total waiting for maturity: {len(self.waiting_t0_tokens)}")
        else:
            logger.info("No new pools found in this discovery pass.")

        return new_count


    async def process_waiting_t0_pools(self) -> int:
        """Checks waiting pools and evaluates them exactly when they cross 15m maturity."""
        processed_count = 0
        now = time.time()
        
        # Make a copy of keys to avoid dict size changed during iteration
        for pool_address in list(self.waiting_t0_tokens.keys()):
            data = self.waiting_t0_tokens.get(pool_address)
            if not data:
                continue
                
            pool_created_at_str = data.get("pool_created_at")
            if not pool_created_at_str:
                age_seconds = now - data.get("discovery_time", now)
            else:
                try:
                    from datetime import datetime, timezone
                    pool_dt = datetime.fromisoformat(pool_created_at_str.replace('Z', '+00:00'))
                    age_seconds = (datetime.now(timezone.utc) - pool_dt).total_seconds()
                except Exception as e:
                    logger.warning(f"Failed to parse pool_created_at '{pool_created_at_str}': {e}")
                    age_seconds = now - data.get("discovery_time", now)
            
            if age_seconds >= 900:  # 15 minutes
                logger.info(f"Pool {data.get('symbol')} ({pool_address}) reached 15m maturity. Fetching fresh T0 data...")
                
                # Fetch fresh data from GeckoTerminal
                pool_data = await api_client.fetch_geckoterminal_pool(network=self.network, pool_address=pool_address)
                if not pool_data:
                    # GT dropped it or 404
                    snapshot = {
                        "pool_address": pool_address,
                        "token_address": data.get("token_address"),
                        "symbol": data.get("symbol"),
                        "raw_symbol": data.get("symbol", "").split(" (")[0],
                        "network": self.network,
                        "status": "DROPPED",
                        "drop_reason": "Failed to fetch updated GT pool info at T0",
                        "outcome_label": "Failed to fetch",
                        "outcome_reason": "GeckoTerminal returned empty pool data at 15m maturity.",
                        "tfinal_timestamp": now,
                    }
                    self.resolved_tokens.append(snapshot)
                    self._save_resolved_tokens()
                    del self.waiting_t0_tokens[pool_address]
                    self._save_waiting_t0_tokens()
                    continue
                
                attributes = pool_data.get("attributes", {})
                price_usd = float(attributes.get("base_token_price_usd") or 0.0)
                liquidity_usd = float(attributes.get("reserve_in_usd") or 0.0)
                mcap_usd = float(attributes.get("fdv_usd") or 0.0)
                
                volume_dict = attributes.get("volume_usd", {})
                vol_15m = float(volume_dict.get("m5", 0.0) or volume_dict.get("h1", 0.0) or 0.0)
                
                # Guardrail: Check for impossible 0/0 values indicating a broken fetch
                if mcap_usd == 0 and liquidity_usd == 0:
                    logger.warning(f"Guardrail tripped for {data.get('symbol')} ({pool_address}): GT returned $0 MCap and $0 Liq. Likely API bug.")
                    snapshot = {
                        "pool_address": pool_address,
                        "token_address": data.get("token_address"),
                        "symbol": data.get("symbol"),
                        "raw_symbol": data.get("symbol", "").split(" (")[0],
                        "network": self.network,
                        "status": "DROPPED",
                        "drop_reason": "Data fetch likely broken ($0 mcap/liq)",
                        "outcome_label": "Failed to fetch",
                        "outcome_reason": "GeckoTerminal returned impossible $0 values.",
                        "tfinal_timestamp": now,
                    }
                    self.resolved_tokens.append(snapshot)
                    self._save_resolved_tokens()
                    del self.waiting_t0_tokens[pool_address]
                    self._save_waiting_t0_tokens()
                    continue

                # Check bounds again
                if mcap_usd < 5000.0 or mcap_usd > 500000.0 or liquidity_usd < 1000.0:
                    logger.debug(f"Skipping matured pool {data.get('symbol')} (Out of bounds: MCap ${mcap_usd:,.0f}, Liq ${liquidity_usd:,.0f})")
                    snapshot = {
                        "pool_address": pool_address,
                        "token_address": data.get("token_address"),
                        "symbol": data.get("symbol"),
                        "raw_symbol": data.get("symbol", "").split(" (")[0],
                        "network": self.network,
                        "status": "DROPPED",
                        "drop_reason": "Out of bounds at 15m maturity",
                        "outcome_label": "Dropped",
                        "outcome_reason": f"Matured out of bounds (MCap: ${mcap_usd:,.0f}, Liq: ${liquidity_usd:,.0f})",
                        "tfinal_timestamp": now,
                    }
                    self.resolved_tokens.append(snapshot)
                    self._save_resolved_tokens()
                    del self.waiting_t0_tokens[pool_address]
                    self._save_waiting_t0_tokens()
                    continue

                # Birdeye Forensics Fetch (First 15m)
                launch_timestamp = int(pool_dt.timestamp()) if 'pool_dt' in locals() else int(now - 900)
                birdeye_swaps = await api_client.fetch_birdeye_swaps(
                    token_address=data.get("token_address"),
                    launch_timestamp=launch_timestamp,
                    max_pages=10
                )
                
                forensics = {
                    "t0_unique_buyers": 0,
                    "t0_single_wallet_vol_pct": 0.0,
                    "t0_median_buy_size_usd": 0.0,
                    "t0_forensics_collected": False
                }
                
                if birdeye_swaps:
                    buyer_wallets = set()
                    wallet_volumes = {}
                    buy_sizes_usd = []
                    total_volume_usd = 0.0
                    
                    for swap in birdeye_swaps:
                        owner = swap.get("owner")
                        side = swap.get("side")
                        if not owner or not side:
                            continue
                            
                        # Extract USD value (using the from price as a proxy)
                        from_data = swap.get("from", {})
                        price = from_data.get("price", 0.0)
                        ui_amount = from_data.get("uiAmount", 0.0)
                        if price is None: price = 0.0
                        if ui_amount is None: ui_amount = 0.0
                        usd_value = float(price * ui_amount)
                        
                        total_volume_usd += usd_value
                        wallet_volumes[owner] = wallet_volumes.get(owner, 0.0) + usd_value
                        
                        if side == "buy":
                            buyer_wallets.add(owner)
                            buy_sizes_usd.append(usd_value)
                            
                    t0_unique_buyers = len(buyer_wallets)
                    max_wallet_vol = max(wallet_volumes.values()) if wallet_volumes else 0.0
                    t0_single_wallet_vol_pct = (max_wallet_vol / total_volume_usd * 100.0) if total_volume_usd > 0 else 0.0
                    
                    t0_median_buy_size_usd = 0.0
                    if buy_sizes_usd:
                        buy_sizes_usd.sort()
                        n = len(buy_sizes_usd)
                        if n % 2 == 1:
                            t0_median_buy_size_usd = buy_sizes_usd[n // 2]
                        else:
                            t0_median_buy_size_usd = (buy_sizes_usd[n // 2 - 1] + buy_sizes_usd[n // 2]) / 2.0
                            
                    forensics = {
                        "t0_unique_buyers": t0_unique_buyers,
                        "t0_single_wallet_vol_pct": round(t0_single_wallet_vol_pct, 2),
                        "t0_median_buy_size_usd": round(t0_median_buy_size_usd, 2),
                        "t0_forensics_collected": True
                    }
                    logger.info(f"Birdeye Forensics collected for {data.get('symbol')}: {t0_unique_buyers} buyers, max wallet {t0_single_wallet_vol_pct:.1f}%")
                else:
                    logger.warning(f"No Birdeye trades found for {data.get('symbol')} or fetch failed. Forensics marked False.")

                snapshot = await self._capture_t0_snapshot(
                    pool_address=pool_address,
                    token_address=data.get("token_address"),
                    symbol=data.get("symbol"),
                    price_usd=price_usd,
                    liquidity_usd=liquidity_usd,
                    mcap_usd=mcap_usd,
                    vol_15m=vol_15m,
                    age_hours=age_seconds / 3600.0,
                    has_rtl_scam=data.get("has_rtl_scam", False),
                    forensics=forensics,
                )

                if snapshot.get("status") == "DROPPED":
                    self.resolved_tokens.append(snapshot)
                    self._save_resolved_tokens()
                else:
                    self.pending_tokens[pool_address] = snapshot
                    self._save_pending_tokens()
                    logger.info(f"T0 snapshot captured and queued for {data.get('symbol')} (Age: {age_seconds/60:.1f}m)")

                del self.waiting_t0_tokens[pool_address]
                self._save_waiting_t0_tokens()
                processed_count += 1
                await asyncio.sleep(0.3)
                
        if processed_count > 0:
            logger.info(f"Processed {processed_count} matured pools into pending_tokens. Total waiting: {len(self.waiting_t0_tokens)}")
            
        return processed_count

    async def _capture_t0_snapshot(
        self,
        pool_address: str,
        token_address: str,
        symbol: str,
        price_usd: float,
        liquidity_usd: float,
        mcap_usd: float,
        vol_15m: float,
        age_hours: float,
        has_rtl_scam: bool = False,
        forensics: dict = None,
    ) -> dict[str, Any]:
        """Runs immediate RPC calls for Gates 1, 4, 5, 9, 11a, 11b at launch moment (T0)."""
        liq_mcap_ratio = round(liquidity_usd / mcap_usd, 4) if mcap_usd > 0 else 0.0
        short_addr = f" ({token_address[:5]}...)" if token_address and len(token_address) >= 5 else ""
        display_symbol = f"{symbol}{short_addr}"

        snapshot = {
            "pool_address": pool_address,
            "token_address": token_address,
            "symbol": display_symbol,
            "raw_symbol": symbol,
            "network": self.network,
            "t0_timestamp": int(time.time()),
            "t0_date": datetime.now(timezone.utc).isoformat(),
            "age_hours": age_hours,
            "t0_price_usd": price_usd,
            "t0_liquidity_usd": liquidity_usd,
            "t0_mcap_usd": mcap_usd,
            "t0_volume_usd_15m": vol_15m,
            "t0_top10_holder_pct": 15.0,
            "t0_dev_wallet_pct": 1.0,
            "t0_lp_locked_days": 0,
            "t0_is_token_2022": False,
            "t0_has_malicious_extensions": False,
            "t0_has_rtl_scam": has_rtl_scam,
            "t0_buy_sell_ratio": 0.0,
            "t0_holder_count_exact": None,
            "t0_holder_count_floor": None,
            "t0_holder_count_capped": False,
            "t0_avg_tx_size": 0.0,
            "t0_single_wallet_vol_pct": forensics.get("t0_single_wallet_vol_pct", 0.0) if forensics else 0.0,
            "t0_unique_buyers": forensics.get("t0_unique_buyers", 0) if forensics else 0,
            "t0_median_buy_size_usd": forensics.get("t0_median_buy_size_usd", 0.0) if forensics else 0.0,
            "pool_slot": 0,                      # Left unpopulated for Gate 12
            "creator_funding_slot": 0,           # Left unpopulated for Gate 12
            "pool_time": 0,                   
            "t0_slot_data_collected": False,     # Explicit flag to avoid 0-sentinel ambiguity
            "t0_forensics_collected": forensics.get("t0_forensics_collected", False) if forensics else False,
            "t0_ratio_window": "",
            "liq_mcap_ratio": liq_mcap_ratio,
            "status": "PENDING",
            "drop_reason": None,
        }

        if self.network == "solana" and token_address:
            # 1. Token-2022 & Extensions Check (Gate 11a/11b)
            token_info = await api_client.fetch_token_account_info(token_address)
            if token_info:
                owner = token_info.get("owner", "")
                if owner == "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb":
                    snapshot["t0_is_token_2022"] = True
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
                                        snapshot["t0_has_malicious_extensions"] = True
                                    elif ext_type == 12: # DefaultAccountState
                                        if offset + 4 + 1 <= len(raw_data) and raw_data[offset+4] == 2:
                                            snapshot["t0_has_malicious_extensions"] = True
                                    offset += 4 + ext_len
                        except Exception:
                            pass

            # 2. T0 Real-Time Holder & Dev Wallet Check (Gates 4 & 5)
            supply = await api_client.fetch_solana_token_supply(token_address)
            accounts = await api_client.fetch_solana_token_largest_accounts(token_address)

            if supply and accounts and supply > 0:
                # Filter out system burn addresses
                ex_burn_accounts = [acc for acc in accounts if acc["address"] not in SOLANA_BURN_ADDRESSES]
                
                # Exclude AMM Liquidity Vaults / Bonding Curves using true on-chain identity
                KNOWN_AMM_PROGRAM_IDS = {
                    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", # Raydium v4
                    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1", # Raydium v4
                    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C", # Raydium CPMM
                    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK", # Raydium CLMM
                    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", # Pump.fun
                    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA", # Pump.fun AMM
                    "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG", # Meteora Dynamic AMM
                    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB", # Meteora DAMM v2
                    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo", # Meteora DLMM
                    "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN", # Meteora DBC
                    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc", # Orca Whirlpools
                }
                non_vault_accounts = []
                for acc in ex_burn_accounts:
                    # Check large accounts (>5% supply) to see if they are actually AMM program vaults
                    # by checking if their authority (the wallet) is owned by an AMM program (i.e. a PDA)
                    # instead of the System Program (11111111111111111111111111111111).
                    if acc["uiAmount"] / supply > 0.05:
                        authority = await api_client.fetch_token_account_authority(acc["address"])
                        if authority:
                            sys_owner = await api_client.fetch_account_owner(authority)
                            if sys_owner in KNOWN_AMM_PROGRAM_IDS:
                                logger.info(f"Excluded AMM vault account: {acc['address']} (Authority: {authority}, Owner: {sys_owner})")
                                continue
                    non_vault_accounts.append(acc)

                top10_sum = sum(acc["uiAmount"] for acc in non_vault_accounts[:10])
                snapshot["t0_top10_holder_pct"] = round((top10_sum / supply) * 100.0, 2)

                if non_vault_accounts:
                    snapshot["t0_dev_wallet_pct"] = round((non_vault_accounts[0]["uiAmount"] / supply) * 100.0, 2)
                else:
                    snapshot["t0_dev_wallet_pct"] = 0.0

            # 3. Real-Time LP Lock/Burn Check (Gate 1)
            lp_mint = await api_client.fetch_pool_lp_mint(pool_address)
            if lp_mint == "PROGRAM_LOCKED":
                snapshot["t0_lp_locked_days"] = 365
            elif lp_mint:
                lp_supply = await api_client.fetch_solana_token_supply(lp_mint)
                lp_accounts = await api_client.fetch_solana_token_largest_accounts(lp_mint)
                if lp_supply and lp_accounts and lp_supply > 0:
                    for acc in lp_accounts[:3]:
                        if acc["address"] in SOLANA_BURN_ADDRESSES and (acc["uiAmount"] / lp_supply) >= 0.80:
                            snapshot["t0_lp_locked_days"] = 365
                            break

            # 4. T0 Tier 3 Metrics via DexScreener (Gate 6 proxy, Gate 7, Gate 13)
            dex_data = await api_client.fetch_dexscreener_tokens([token_address])
            if not dex_data:
                logger.error(f"DexScreener payload completely empty or missing for {token_address}")
                snapshot["status"] = "DROPPED"
                snapshot["outcome_label"] = "Data Incomplete"
                snapshot["outcome_reason"] = "DexScreener payload completely empty"
                snapshot["drop_reason"] = "data_incomplete_dexscreener"
                return snapshot
            
            # Find the matching pair by pool address, or fallback to the most liquid pair
            target_pair = next((p for p in dex_data if p.get("pairAddress", "").lower() == pool_address.lower()), dex_data[0])
            
            txns = target_pair.get("txns", {})
            volume_dict = target_pair.get("volume", {})
            
            if "m5" not in txns and "h1" not in txns:
                logger.error(f"DexScreener payload missing txns data for {token_address} (missing both txns.m5 and txns.h1). Dropping token.")
                snapshot["status"] = "DROPPED"
                snapshot["outcome_label"] = "Data Incomplete"
                snapshot["outcome_reason"] = "DexScreener missing txns data"
                snapshot["drop_reason"] = "data_incomplete_dexscreener"
                return snapshot
            elif "m5" not in txns:
                logger.warning(f"DexScreener payload missing txns.m5 for {token_address} (falling back to txns.h1)")
                
            m5_tx = txns.get("m5", {})
            h1_tx = txns.get("h1", {})
            
            m5_buys = m5_tx.get("buys", 0)
            m5_sells = m5_tx.get("sells", 0)
            h1_buys = h1_tx.get("buys", 0)
            h1_sells = h1_tx.get("sells", 0)
            
            t0_ratio_window = ""
            t0_buy_sell_ratio = 0.0
            t0_avg_tx_size = 0.0

            if (m5_buys + m5_sells) > 0:
                snapshot["t0_ratio_window"] = "m5"
                snapshot["t0_buy_sell_ratio"] = round(m5_buys / m5_sells, 2) if m5_sells > 0 else float(m5_buys)
                total_tx = m5_buys + m5_sells
                vol_window = float(volume_dict.get("m5", 0.0))
            elif (h1_buys + h1_sells) > 0:
                snapshot["t0_ratio_window"] = "h1"
                snapshot["t0_buy_sell_ratio"] = round(h1_buys / h1_sells, 2) if h1_sells > 0 else float(h1_buys)
                total_tx = h1_buys + h1_sells
                vol_window = float(volume_dict.get("h1", 0.0))
            else:
                total_tx = 0
                vol_window = 0.0
                
            if total_tx > 0:
                snapshot["t0_avg_tx_size"] = round(vol_window / total_tx, 2)

            holder_count = await api_client.fetch_helius_das_holder_count(token_address, limit=100)
            if holder_count is None:
                logger.error(f"Failed to fetch holder count from Helius DAS for {token_address}. Dropping token.")
                snapshot["status"] = "DROPPED"
                snapshot["outcome_label"] = "Data Incomplete"
                snapshot["outcome_reason"] = "Failed to fetch Helius DAS holder count"
                snapshot["drop_reason"] = "data_incomplete_helius_das"
                return snapshot
            
            snapshot["t0_holder_count_capped"] = holder_count >= 100
            snapshot["t0_holder_count_exact"] = holder_count if not snapshot["t0_holder_count_capped"] else None
            snapshot["t0_holder_count_floor"] = 100 if snapshot["t0_holder_count_capped"] else None

        return snapshot

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

            t0_liq = snapshot.get("t0_liquidity_usd", 0.0)
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

            # Gate 4 & 5 verification against outcome status
            t0_top10 = snapshot.get("t0_top10_holder_pct", 100.0)
            t0_dev = snapshot.get("t0_dev_wallet_pct", 100.0)
            passed_gate4 = t0_top10 <= settings.GATE_4_TOP10_HOLDER_MAX_PCT
            passed_gate5 = t0_dev <= settings.GATE_5_DEV_WALLET_MAX_PCT

            # Outcome Classification
            if roi >= 2.0:
                if passed_gate4 and passed_gate5:
                    label = "Winner"
                    reason = f"{win_str} ROI was {roi:.2f}x"
                else:
                    label = "Scam / washed"
                    reason = f"ROI {roi:.2f}x but failed Gate 4/5 (Top10: {t0_top10}%, Dev: {t0_dev}%)"
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
                
                # 1. Discover fresh pools & queue for 15m maturity
                try:
                    await self.discover_and_snapshot(pages=10)
                except Exception as e:
                    logger.error(f"Error during discovery pass: {e}")

                # 2. Process waiting pools that reached 15m maturity
                try:
                    await self.process_waiting_t0_pools()
                except Exception as e:
                    logger.error(f"Error processing waiting pools: {e}")

                # 3. Check for 24h matured tokens & compute ROI outcomes
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

if __name__ == "__main__":
    runner = ShadowRunner(network="solana")
    try:
        asyncio.run(runner.run_loop(poll_interval=300, eval_delay_seconds=86400))
    except KeyboardInterrupt:
        print("Bot stopped by user.")
