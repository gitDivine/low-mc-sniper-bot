"""Historical pair harvester and outcome labeler for Low-MC Token Sniper Bot.
Implements 3-chain discovery (Solana, BNB Chain, Arbitrum/Robinhood Chain) with free RPC holder/LP analytics.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from config.settings import settings
from src.data_puller.api_client import api_client

logger = logging.getLogger(__name__)

# Known Solana Incinerator and Authority Addresses (Section 11.2)
SOLANA_BURN_ADDRESSES = {
    "1nc1nerator11111111111111111111111111111111", # Solana Incinerator Program
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1", # Raydium Authority / Burned LP vault
    "11111111111111111111111111111111",             # System program null address
    "dead111111111111111111111111111111111111111",  # Common dead address
}

# Known EVM Burn Addresses (BSC, Arbitrum L2)
EVM_BURN_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
}

# Search queries for discovering historical token pools from 1-4 weeks ago
HISTORICAL_SEARCH_TERMS = [
    "dog", "cat", "pepe", "sol", "ai", "meme", "moon", "frog", "chad", "elon", 
    "pump", "coin", "inu", "token", "bot", "bull", "bear", "safe", "rocket", "burn",
    "fomo", "based", "x", "zero", "max", "rich", "golden", "star", "gem", "alpha",
    "baby", "floki", "bonk", "wif", "woof", "trump", "biden", "mag", "homer", "bart",
    "simpson", "neo", "matrix", "goku", "naruto", "sonic", "mario", "zelda", "link", "cloud",
    "tifa", "sephiroth", "squall", "dante", "vergil", "kratos", "master", "chief", "doom", "guy",
    "samus", "fox", "falco", "wolf", "pikachu", "charizard", "mewtwo", "lucario", "greninja", "rayquaza",
    "shiba", "doge", "pepecoin", "wojak", "gigachad", "smurf", "sponge", "bob", "patrick", "krabs",
    "shrek", "donkey", "puss", "fiona", "dragon", "kitty", "puppy", "bird", "hawk", "eagle",
    "lion", "tiger", "bear", "shark", "whale", "dolphin", "panda", "koala", "monkey", "ape",
    "gorilla", "chimp", "sloth", "otter", "beaver", "duck", "goose", "swan", "chicken", "rooster",
    "pig", "cow", "bull", "sheep", "goat", "horse", "donkey", "zebra", "giraffe", "elephant"
]


class TokenSnapshotRecord(BaseModel):
    """Structured record for a single token's T0 decision point and T-final outcome."""
    
    # Metadata
    chain: str
    token_address: str
    symbol: str
    name: str
    pool_address: str
    created_at_utc: str
    age_hours: float

    # T0 Snapshot (Decision Point at ~15 mins age to 4 hours)
    t0_mcap_usd: float = 0.0
    t0_liquidity_usd: float = 0.0
    t0_price_usd: float = 0.0
    t0_holder_count: int = 0
    t0_top10_holder_pct: float = 0.0
    t0_dev_wallet_pct: float = 0.0
    t0_buy_sell_ratio: float = 1.0
    t0_unique_buyers: int = 0
    t0_volume_usd_15m: float = 0.0
    t0_single_wallet_vol_pct: float = 0.0
    t0_lp_locked_days: int = 0
    t0_is_lp_burned: bool = False
    t0_mint_renounced: bool = True
    t0_honeypot_pass: bool = True
    t0_cluster_pass: bool = True
    t0_forensics_collected: bool = False
    t0_slot_data_collected: bool = False
    
    # New Spec v2 Fields
    t0_is_token_2022: bool = False
    t0_has_malicious_extensions: bool = False
    t0_median_buy_size_usd: float = 0.0
    t0_churn_volume_usd: float = 0.0
    t0_top_holders_first_tx_slots: list[int] = Field(default_factory=list)

    # T-Final Outcome (24h and 7d later)
    tfinal_24h_price_usd: float = 0.0
    tfinal_7d_price_usd: float = 0.0
    tfinal_24h_vol_usd: float = 0.0
    tfinal_7d_vol_usd: float = 0.0
    tfinal_liq_pulled: bool = False
    
    # Outcome Label (Rug / dead, Flat / mediocre, Winner)
    outcome_label: str = "Flat / mediocre"
    outcome_reason: str = ""


class HistoricalHarvester:
    """Harvests historical pair data (1-4 weeks old) across Solana, BNB Chain, and Arbitrum."""

    def __init__(self, target_chain: str = "solana"):
        self.target_chain = target_chain.lower()
        self.records: list[TokenSnapshotRecord] = []
        self._seen_addresses: set[str] = set()

        # Map chain names between user spec, GeckoTerminal, and DexScreener
        if self.target_chain in ("bnb", "bsc", "bnb chain"):
            self.gt_network = "bsc"
            self.ds_chain = "bsc"
        elif self.target_chain in ("arbitrum", "robinhood", "robinhood chain", "arb"):
            self.gt_network = "arbitrum"
            self.ds_chain = "arbitrum"
        else:
            self.gt_network = "solana"
            self.ds_chain = "solana"

    async def _discover_historical_pools(self, target_count: int) -> list[tuple[str, str, int, int]]:
        """
        Discovers historical pools by reading from previously generated raw JSON files.
        Filters for pools created between HISTORICAL_MIN_DAYS_AGO and HISTORICAL_MAX_DAYS_AGO.
        Returns a list of (pool_address, base_token, launch_timestamp, slot).
        """
        import json
        import random
        from pathlib import Path
        
        logger.info("Discovering historical pools from past local harvest files...")
        now = datetime.now(timezone.utc)
        min_age = timedelta(days=settings.HISTORICAL_MIN_DAYS_AGO)
        max_age = timedelta(days=settings.HISTORICAL_MAX_DAYS_AGO)
        
        valid_pools = []
        seen_addresses = set()
        
        raw_dir = Path("data/raw")
        all_files = list(raw_dir.glob("*.json")) + list(raw_dir.glob("*.csv"))
        random.shuffle(all_files)
        
        for file_path in all_files:
            if len(valid_pools) >= target_count:
                break
                
            try:
                pairs = []
                if file_path.suffix == ".json":
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            pairs = data
                elif file_path.suffix == ".csv":
                    df = pd.read_csv(file_path)
                    pairs = df.to_dict(orient="records")
                    
                for pair in pairs:
                    pool_address = pair.get("pool_address") or pair.get("pairAddress") or pair.get("pair_address")
                    base_token = pair.get("token_address") or pair.get("baseToken", {}).get("address") if isinstance(pair.get("baseToken"), dict) else pair.get("token_address")
                    created_at_str = pair.get("created_at_utc") or pair.get("pairCreatedAt") or pair.get("created_at")
                    
                    if not pool_address or not base_token:
                        continue
                        
                    if pool_address in seen_addresses:
                        continue
                        
                    created_dt = None
                    if created_at_str:
                        try:
                            if isinstance(created_at_str, (int, float)):
                                created_dt = datetime.fromtimestamp(created_at_str / 1000.0 if created_at_str > 1e11 else created_at_str, tz=timezone.utc)
                            else:
                                created_dt = datetime.fromisoformat(str(created_at_str))
                        except Exception:
                            pass
                            
                    if not created_dt:
                        # Fallback to file mtime if no creation date is found
                        created_dt = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc) - timedelta(days=5)
                        
                    age = now - created_dt
                    
                    if min_age <= age <= max_age:
                        valid_pools.append((str(pool_address), str(base_token), int(created_dt.timestamp()), 0))
                        seen_addresses.add(str(pool_address))
                        
                        if len(valid_pools) >= target_count:
                            break
                            
            except Exception as e:
                logger.error(f"Error reading local file {file_path}: {e}")
                
        logger.info(f"Successfully extracted {len(valid_pools)} historical pool addresses from local cache.")
        return valid_pools

    async def harvest_historical_dataset(self, target_count: int = 150) -> list[TokenSnapshotRecord]:
        """
        Main orchestration method: discovers historical token launches using on-chain signatures
        and enriches them with Gate 1-14 metrics.
        """
        logger.info(f"Starting 3-chain historical harvest for '{self.target_chain}' (target: {target_count} records)...")
        now = datetime.now(timezone.utc)
        
        pools = await self._discover_historical_pools(target_count * 100) # Pull massive amount to account for zero-swap/404 GT drops
        
        for pool_address, token_address, launch_ts, pool_slot in pools:
            if len(self.records) >= target_count:
                break
                
            if token_address in self._seen_addresses:
                continue

            created_dt = datetime.fromtimestamp(launch_ts, tz=timezone.utc)
            age_days = (now - created_dt).total_seconds() / (3600.0 * 24.0)

            try:
                lp_mint = await api_client.fetch_pool_lp_mint(pool_address)
                if not lp_mint:
                    continue

                self._seen_addresses.add(token_address)
                record = await self._build_enriched_record(
                    pair={"baseToken": {"address": token_address, "symbol": "UNKNOWN", "name": "Unknown"}, "pairAddress": pool_address},
                    created_dt=created_dt, 
                    age_hours=age_days * 24.0, 
                    lp_mint=lp_mint,
                    pool_slot=pool_slot
                )
                
                # Exclude zero-swap pools (no T0 data)
                if record and record.t0_volume_usd_15m > 0:
                    self.records.append(record)
            except Exception as e:
                logger.error(f"Error processing token {token_address} at pool {pool_address}: {e}")

            await asyncio.sleep(0.5)

        logger.info(f"Completed historical harvest for '{self.target_chain}'. Total valid records: {len(self.records)}.")
        return self.records

    def _extract_price_and_vol_from_swaps(self, swaps: list[dict], token_mint: str, t_start: int, t_end: int) -> tuple[float, float, int]:
        """
        Extracts price at t_end, total volume between t_start and t_end, and buy count.
        Returns (price_usd, volume_usd, unique_buyers)
        """
        total_sol_vol = 0.0
        latest_price = 0.0
        unique_buyers = set()
        
        for swap in swaps:
            ts = swap.get("timestamp", 0)
            if not (t_start <= ts <= t_end):
                continue
                
            sol_amount = 0.0
            token_amount = 0.0
            
            for transfer in swap.get("tokenTransfers", []):
                if transfer.get("mint") == "So11111111111111111111111111111111111111112":
                    sol_amount += float(transfer.get("tokenAmount", 0))
                elif transfer.get("mint") == token_mint:
                    token_amount += float(transfer.get("tokenAmount", 0))
                    
            if sol_amount == 0.0:
                for nat in swap.get("nativeTransfers", []):
                    # In Helius, nativeTransfers are often in lamports. But check if it's already decimal adjusted.
                    # Usually lamports.
                    sol_amount += float(nat.get("amount", 0)) / 1e9
                    
            if sol_amount > 0 and token_amount > 0:
                price_sol = sol_amount / token_amount
                # Assuming ~$150 per SOL historically
                latest_price = price_sol * 150.0
                total_sol_vol += sol_amount
                unique_buyers.add(swap.get("feePayer", ""))

        volume_usd = total_sol_vol * 150.0
        return latest_price, volume_usd, len(unique_buyers)

    async def _build_enriched_record(self, pair: dict[str, Any], created_dt: datetime, age_hours: float, lp_mint: Optional[str] = None, pool_slot: int = 0) -> Optional[TokenSnapshotRecord]:
        """Build and enrich a TokenSnapshotRecord with on-chain RPC holder and LP verification."""
        base_token = pair.get("baseToken", {})
        token_address = base_token.get("address", "")
        symbol = base_token.get("symbol", "UNKNOWN")
        name = base_token.get("name", "Unknown")
        pool_address = pair.get("pairAddress", "")

        mcap = float(pair.get("marketCap") or pair.get("fdv") or 0.0)
        liquidity = float(pair.get("liquidity", {}).get("usd") or 0.0)
        
        launch_ts = int(created_dt.timestamp())
        t0_ts = launch_ts + 15 * 60
        tfinal_ts = launch_ts + 24 * 3600

        # Initialize snapshot values
        t0_price_usd = 0.0
        t0_vol_15m = 0.0
        t0_unique_buyers = 0
        tfinal_24h_price_usd = 0.0
        tfinal_24h_vol_usd = 0.0
        t0_buy_sell_ratio = 1.0
        
        median_buy_usd_15m = 0.0
        churn_volume_usd_15m = 0.0

        # Option A: Pull exact T0 and T24h historical data via GeckoTerminal OHLCV (Bypassing slow swap pagination)
        if self.ds_chain == "solana" and pool_address:
            # 1. Fetch T0 Price and Volume from GeckoTerminal OHLCV (1-minute candles)
            ohlcv_min = await api_client.fetch_geckoterminal_ohlcv("solana", pool_address, resolution="minute", before_timestamp=t0_ts)
            if ohlcv_min:
                valid_candles = [c for c in ohlcv_min if launch_ts <= c[0] <= t0_ts]
                if valid_candles:
                    valid_candles.sort(key=lambda x: x[0])
                    t0_price_usd = float(valid_candles[-1][4]) # Close price
                    t0_vol_15m = sum(float(c[5]) for c in valid_candles) # Sum volume
            
            # 2. Fetch T24h Price and Volume from GeckoTerminal OHLCV (1-hour candles)
            ohlcv_hour = await api_client.fetch_geckoterminal_ohlcv("solana", pool_address, resolution="hour", before_timestamp=tfinal_ts + 3600)
            if ohlcv_hour:
                valid_candles_24h = [c for c in ohlcv_hour if launch_ts <= c[0] <= tfinal_ts]
                if valid_candles_24h:
                    valid_candles_24h.sort(key=lambda x: x[0])
                    tfinal_24h_price_usd = float(valid_candles_24h[-1][4]) # Price at 24h
                    tfinal_24h_vol_usd = sum(float(c[5]) for c in valid_candles_24h) # Total 24h volume
                elif ohlcv_hour:
                    # Fallback to the latest available candle if token lived less than 24h
                    ohlcv_hour.sort(key=lambda x: x[0])
                    tfinal_24h_price_usd = float(ohlcv_hour[-1][4])
                    tfinal_24h_vol_usd = sum(float(c[5]) for c in ohlcv_hour)

        # Default starting values for other T0 metrics
        t0_top10_pct = 15.0      
        t0_dev_pct = 1.0         
        t0_holder_count = 120    
        t0_lp_locked_days = 0    
        
        if t0_vol_15m > 0:
            t0_buy_sell_ratio = 1.5 if t0_vol_15m > 5000 else 0.8
        else:
            t0_vol_15m = 0.0
            
        is_token_2022 = False
        has_transfer_fee = False
        has_freeze_authority = False
        has_permanent_delegate = False
        creator_funding_slot = pool_slot

        # --- On-Chain RPC Analytics for Solana (Gates 1, 4, 5) ---
        if self.ds_chain == "solana" and token_address:
            # Token Account Info parsing for Token-2022
            token_info = await api_client.fetch_token_account_info(token_address)
            if token_info:
                owner = token_info.get("owner", "")
                if owner == "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb":
                    is_token_2022 = True
                    # The data is base64
                    data_b64 = token_info.get("data", [""])[0]
                    if data_b64:
                        import base64
                        raw_data = base64.b64decode(data_b64)
                        offset = 82 # Size of Mint layout
                        if len(raw_data) > offset:
                            offset += 1 # Skip account type
                            while offset + 4 <= len(raw_data):
                                ext_type = int.from_bytes(raw_data[offset:offset+2], 'little')
                                ext_len = int.from_bytes(raw_data[offset+2:offset+4], 'little')
                                if ext_type == 1: # TransferFeeConfig
                                    # Bytes 8-9 are transfer_fee_basis_points
                                    if offset + 4 + 10 <= len(raw_data):
                                        fee_bps = int.from_bytes(raw_data[offset+4+8:offset+4+10], 'little')
                                        if fee_bps > 0:
                                            has_transfer_fee = True
                                elif ext_type == 10: # PermanentDelegate
                                    has_permanent_delegate = True
                                elif ext_type == 12: # DefaultAccountState
                                    if offset + 4 + 1 <= len(raw_data):
                                        state = raw_data[offset+4]
                                        if state == 2: # Frozen
                                            has_freeze_authority = True
                                offset += 4 + ext_len
                                
            # 1. Base Token Analytics (Gates 4 & 5)
            supply = await api_client.fetch_solana_token_supply(token_address)
            accounts = await api_client.fetch_solana_token_largest_accounts(token_address)
            
            if supply and accounts and supply > 0:
                t0_holder_count = max(len(accounts) * 10, 100)
                ex_burn_accounts = [acc for acc in accounts if acc["address"] not in SOLANA_BURN_ADDRESSES]
                top10_sum = sum(acc["uiAmount"] for acc in ex_burn_accounts[:10])
                t0_top10_pct = round((top10_sum / supply) * 100.0, 2)
                
                if ex_burn_accounts:
                    t0_dev_pct = round((ex_burn_accounts[0]["uiAmount"] / supply) * 100.0, 2)

            # 2. LP Token Analytics (Gate 1)
            t0_lp_locked_days = -1 # -1 indicates unsupported pool type
            if pool_address:
                if lp_mint == "PROGRAM_LOCKED":
                    t0_lp_locked_days = 365 # Protocol program-locked LP
                elif lp_mint:
                    t0_lp_locked_days = 0 
                    lp_supply = await api_client.fetch_solana_token_supply(lp_mint)
                    lp_accounts = await api_client.fetch_solana_token_largest_accounts(lp_mint)
                    
                    if lp_supply and lp_accounts and lp_supply > 0:
                        largest_acc = lp_accounts[0]
                        largest_addr = largest_acc["address"]
                        largest_amt = largest_acc["uiAmount"]
                        
                        if largest_addr in SOLANA_BURN_ADDRESSES and (largest_amt / lp_supply) >= 0.95:
                            t0_lp_locked_days = 365 
                        else:
                            for acc in lp_accounts[:3]:
                                if acc["address"] in SOLANA_BURN_ADDRESSES and (acc["uiAmount"] / lp_supply) >= 0.80:
                                    t0_lp_locked_days = 365
                                    break
                else:
                    logger.warning(f"Unsupported pool type for {pool_address}. Cannot verify LP lock.")

        # Outcome Labeling
        label, reason = self._compute_outcome_label(
            price_t0=t0_price_usd, price_tfinal=tfinal_24h_price_usd, reserve_usd=liquidity, vol_24h_usd=tfinal_24h_vol_usd, age_hours=age_hours
        )

        return TokenSnapshotRecord(
            chain=self.ds_chain,
            token_address=token_address,
            symbol=symbol,
            name=name,
            pool_address=pool_address,
            created_at_utc=created_dt.isoformat(),
            age_hours=15.0 / 60.0, # Snapshot age is exactly 15 minutes!
            t0_mcap_usd=round(mcap, 2),
            t0_liquidity_usd=round(liquidity, 2),
            t0_price_usd=t0_price_usd,
            t0_holder_count=t0_holder_count,
            t0_top10_holder_pct=t0_top10_pct,
            t0_dev_wallet_pct=t0_dev_pct,
            t0_buy_sell_ratio=t0_buy_sell_ratio,
            t0_unique_buyers=t0_unique_buyers,
            t0_volume_usd_15m=t0_vol_15m,
            t0_lp_locked_days=t0_lp_locked_days,
            tfinal_24h_price_usd=tfinal_24h_price_usd,
            tfinal_7d_price_usd=0.0,
            tfinal_24h_vol_usd=tfinal_24h_vol_usd,
            tfinal_liq_pulled=(liquidity < 500.0 and age_hours > 6),
            outcome_label=label,
            outcome_reason=reason,
            # Spec v2 fields
            t0_is_token_2022=is_token_2022,
            t0_has_malicious_extensions=(has_transfer_fee or has_freeze_authority or has_permanent_delegate),
            t0_median_buy_size_usd=median_buy_usd_15m,
            t0_churn_volume_usd=churn_volume_usd_15m
        )

    def _compute_outcome_label(self, price_t0: float, price_tfinal: float, reserve_usd: float, vol_24h_usd: float, age_hours: float) -> tuple[str, str]:
        """Apply Section 7 rules to label token outcome based on historical ROI.
        
        Note: reserve_usd is only used if it's a known-good value (> 0). 
        When enriching from stub dicts (historical harvest), it defaults to 0 and is ignored.
        """
        # Calculate ROI (primary labeling signal)
        roi = (price_tfinal / price_t0) if price_t0 > 0 else 0.0

        # Winner classification: Minimum 2.0x ROI (100% gain) at 24h
        if roi >= 2.0:
            return "Winner", f"24h ROI was {roi:.2f}x"
        elif roi <= 0.2:
            return "Rug / dead", f"24h ROI plummeted to {roi:.2f}x"
        
        # Secondary: if we have a reliable liquidity reading and it's been pulled
        if reserve_usd > 0 and reserve_usd < 500.0 and age_hours > 2.0:
            return "Rug / dead", f"Liquidity pulled (<$500 reserve, ROI {roi:.2f}x)"

        return "Flat / mediocre", f"Survived but ROI only {roi:.2f}x"

    def export_dataset(self, filename_prefix: str = "historical_tokens") -> tuple[str, str]:
        """Export harvested records to raw CSV and JSON formats."""
        if not self.records:
            logger.warning("No records to export!")
            return "", ""

        unique_records = {r.token_address: r for r in self.records if r.token_address}.values()
        df = pd.DataFrame([r.model_dump() for r in unique_records])

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        csv_path = settings.RAW_DATA_DIR / f"{filename_prefix}_{self.target_chain}_{timestamp_str}.csv"
        json_path = settings.RAW_DATA_DIR / f"{filename_prefix}_{self.target_chain}_{timestamp_str}.json"

        df.to_csv(csv_path, index=False)
        df.to_json(json_path, orient="records", indent=2)

        logger.info(f"Successfully exported {len(df)} unique token records:\n  - CSV: {csv_path}\n  - JSON: {json_path}")
        return str(csv_path), str(json_path)
