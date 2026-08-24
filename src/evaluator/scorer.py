"""Offline 14-gate evaluator and statistical cross-tabulation calibrator for Low-MC Token Sniper Bot."""
import json
import logging
from pathlib import Path
from typing import Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from config.settings import settings
from src.data_puller.harvester import TokenSnapshotRecord

logger = logging.getLogger(__name__)


class ScoredTokenRecord(TokenSnapshotRecord):
    """Enriched token record with per-gate pass/fail results and short-circuit failure tracking."""
    
    # Overall Pipeline Result
    passed_all_gates: bool = False
    first_failed_gate: Optional[str] = None
    first_failed_tier: Optional[str] = None
    total_gates_passed: int = 0

    # Individual Gate Results (True = Pass, False = Fail)
    gate_1_lp_lock: bool = False
    gate_2_mint_renounced: bool = False
    gate_3_honeypot: bool = False
    gate_4_top10_holder: bool = False
    gate_5_dev_wallet: bool = False
    gate_6_holder_count: bool = False
    gate_7_buy_sell_ratio: bool = False
    gate_8_single_wallet_vol: Optional[bool] = None  # None = SKIPPED
    gate_9_liq_mcap_ratio: bool = False
    gate_10_unique_buyers: Optional[bool] = None     # None = SKIPPED
    gate_11a_mcap_band: bool = False
    gate_11b_absolute_liq: bool = False
    gate_12_funding_cluster: Optional[bool] = None   # None = SKIPPED
    gate_13_volume_sanity: Optional[bool] = None     # None = SKIPPED
    gate_14_time_in_market: bool = False


class OfflineScorer:
    """Executes the 14-gate short-circuit evaluation pipeline on historical T0 snapshots."""

    def __init__(self):
        self.scored_records: list[ScoredTokenRecord] = []

    def load_dataset(self, file_path: Path) -> list[TokenSnapshotRecord]:
        """Load raw harvested token snapshots from a JSON or CSV file."""
        logger.info(f"Loading raw dataset from {file_path}...")
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        if file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
        elif file_path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path)
            raw_list = df.to_dict(orient="records")
        else:
            raise ValueError(f"Unsupported file extension: {file_path.suffix}")

        normalized = []
        for r in raw_list:
            item = dict(r)
            if "chain" not in item:
                item["chain"] = item.get("network", "solana")
            if "name" not in item:
                item["name"] = item.get("symbol", "Unknown")
            if "created_at_utc" not in item:
                item["created_at_utc"] = item.get("t0_date", "")
            if "age_hours" not in item:
                item["age_hours"] = 0.5
            
            # Map batch 8 holder columns to t0_holder_count
            if "t0_holder_count_exact" in item and not pd.isna(item["t0_holder_count_exact"]):
                item["t0_holder_count"] = int(item["t0_holder_count_exact"])
            elif "t0_holder_count_floor" in item and not pd.isna(item["t0_holder_count_floor"]):
                item["t0_holder_count"] = int(item["t0_holder_count_floor"])
            elif "t0_holder_count_capped" in item and item["t0_holder_count_capped"] == True:
                item["t0_holder_count"] = 50
                
            normalized.append(TokenSnapshotRecord.model_validate(item))

        logger.info(f"Loaded {len(normalized)} token records successfully.")
        return normalized

    def evaluate_all(self, records: list[TokenSnapshotRecord]) -> list[ScoredTokenRecord]:
        """Run the short-circuit evaluation pipeline across all token records."""
        logger.info(f"Running 14-gate short-circuit evaluation on {len(records)} tokens...")
        self.scored_records = [self.evaluate_single(r) for r in records]
        logger.info("Evaluation complete.")
        return self.scored_records

    def evaluate_single(self, record: TokenSnapshotRecord) -> ScoredTokenRecord:
        """
        Evaluate a single token record against the 14 gates strictly in Tier order (Section 4).
        Implements short-circuiting: records the exact first gate and tier failed.
        """
        # Initialize enriched record
        scored = ScoredTokenRecord.model_construct(**record.model_dump())
        gates_passed = 0

        # --- Tier 1: Smart Contract Triage ---
        
        # Gate 1: LP locked >= 30 days OR fully burned
        scored.gate_1_lp_lock = (record.t0_lp_locked_days >= settings.GATE_1_LP_LOCK_MIN_DAYS) or (record.t0_lp_locked_days == 999)
        if not scored.gate_1_lp_lock:
            return self._fail_record(scored, "Gate 1 (LP Not Locked/Burned)", "Tier 1", gates_passed)
        gates_passed += 1

        # Gate 2: Mint/freeze authority renounced
        scored.gate_2_mint_renounced = record.t0_mint_renounced
        if getattr(record, 't0_is_token_2022', False) and getattr(record, 't0_has_malicious_extensions', False):
            scored.gate_2_mint_renounced = False
            
        if not scored.gate_2_mint_renounced:
            return self._fail_record(scored, "Gate 2 (Mint/Freeze Retained)", "Tier 1", gates_passed)
        gates_passed += 1

        # --- Tier 2: Basic Checks + Honeypot ---

        # Gate 3: Not a honeypot
        scored.gate_3_honeypot = record.t0_honeypot_pass
        if getattr(record, 't0_is_token_2022', False) and getattr(record, 't0_has_malicious_extensions', False):
            scored.gate_3_honeypot = False
            
        if not scored.gate_3_honeypot:
            return self._fail_record(scored, "Gate 3 (Honeypot Detected / Token-2022 extensions)", "Tier 2", gates_passed)
        gates_passed += 1

        # Gate 4: Top 10 holders <= 20%
        scored.gate_4_top10_holder = record.t0_top10_holder_pct <= settings.GATE_4_TOP10_HOLDER_MAX_PCT
        if not scored.gate_4_top10_holder:
            return self._fail_record(scored, f"Gate 4 (Top 10 Holders {record.t0_top10_holder_pct}% > {settings.GATE_4_TOP10_HOLDER_MAX_PCT}%)", "Tier 2", gates_passed)
        gates_passed += 1

        # Gate 5: Dev wallet <= 3%
        scored.gate_5_dev_wallet = record.t0_dev_wallet_pct <= settings.GATE_5_DEV_WALLET_MAX_PCT
        if not scored.gate_5_dev_wallet:
            return self._fail_record(scored, f"Gate 5 (Dev Wallet {record.t0_dev_wallet_pct}% > {settings.GATE_5_DEV_WALLET_MAX_PCT}%)", "Tier 2", gates_passed)
        gates_passed += 1

        # --- Gate 11a, 11b, 9: Two-Mode Logic (Micro & Graduate) Preparation ---
        mcap = record.t0_mcap_usd
        liq = record.t0_liquidity_usd
        ratio = (liq / mcap) if mcap > 0 else 0.0

        in_micro = (settings.MODE_MICRO_MIN_MCAP_USD <= mcap <= settings.MODE_MICRO_MAX_MCAP_USD)
        in_grad = (settings.MODE_GRAD_MIN_MCAP_USD <= mcap <= settings.MODE_GRAD_MAX_MCAP_USD)

        pass_liq = False
        pass_ratio = False
        mode_name = ""
        min_liq = 0.0
        min_ratio = 0.0
        max_ratio = 0.0

        if in_micro:
            pass_liq = liq >= settings.MODE_MICRO_MIN_LIQ_USD
            pass_ratio = settings.MODE_MICRO_MIN_LIQ_RATIO <= ratio <= settings.MODE_MICRO_MAX_LIQ_RATIO
            mode_name = "Micro"
            min_liq = settings.MODE_MICRO_MIN_LIQ_USD
            min_ratio = settings.MODE_MICRO_MIN_LIQ_RATIO
            max_ratio = settings.MODE_MICRO_MAX_LIQ_RATIO
        elif in_grad:
            pass_liq = liq >= settings.MODE_GRAD_MIN_LIQ_USD
            pass_ratio = settings.MODE_GRAD_MIN_LIQ_RATIO <= ratio <= settings.MODE_GRAD_MAX_LIQ_RATIO
            mode_name = "Graduate"
            min_liq = settings.MODE_GRAD_MIN_LIQ_USD
            min_ratio = settings.MODE_GRAD_MIN_LIQ_RATIO
            max_ratio = settings.MODE_GRAD_MAX_LIQ_RATIO

        # Gate 11a: Market cap band (Two-Mode Check)
        scored.gate_11a_mcap_band = in_micro or in_grad
        if not scored.gate_11a_mcap_band:
            return self._fail_record(scored, f"Gate 11a (Mcap ${mcap:,.0f} falls in Death Zone or outside limits)", "Tier 2", gates_passed)
        gates_passed += 1

        # Gate 11b: Absolute liquidity floor (Mode-specific)
        scored.gate_11b_absolute_liq = pass_liq
        if not scored.gate_11b_absolute_liq:
            return self._fail_record(scored, f"Gate 11b ({mode_name}: Liq ${liq:,.0f} < ${min_liq:,.0f})", "Tier 2", gates_passed)
        gates_passed += 1

        # Gate 14: Time-in-market (10 mins to 120 mins)
        age_minutes = record.age_hours * 60.0
        scored.gate_14_time_in_market = settings.GATE_14_MIN_AGE_MINUTES <= age_minutes <= settings.GATE_14_MAX_AGE_MINUTES
        if not scored.gate_14_time_in_market:
            return self._fail_record(scored, f"Gate 14 (Age {age_minutes:.1f}m outside {settings.GATE_14_MIN_AGE_MINUTES}-{settings.GATE_14_MAX_AGE_MINUTES}m)", "Tier 2", gates_passed)
        gates_passed += 1

        # --- Tier 3: Momentum & Wash-Trade Filters ---

        # Gate 6: Holder Count >= 50
        scored.gate_6_holder_count = record.t0_holder_count >= settings.GATE_6_MIN_HOLDER_COUNT
        
        if not scored.gate_6_holder_count:
            if record.t0_holder_count == 0:
                return self._fail_record(scored, "Gate 6 (Unindexed Lag: Holder count exactly 0)", "Tier 3", gates_passed)
            else:
                return self._fail_record(scored, f"Gate 6 (Failed Low Holders: {record.t0_holder_count} < {settings.GATE_6_MIN_HOLDER_COUNT})", "Tier 3", gates_passed)
        gates_passed += 1

        # Gate 7: Buy/sell tx ratio
        # Mode-specific behavior:
        # - Micro: Ratio provides no signal (overlapping distributions). Use a loose 0.5 floor as a sanity check.
        # - Graduate: Functions as a secondary anti-manipulation filter. True winners have low ratios (profit taking), 
        #   while wash-traded scams and rugs have extremely high ratios. Enforce a <= 2.5 ceiling.
        if mode_name == "Micro":
            scored.gate_7_buy_sell_ratio = record.t0_buy_sell_ratio >= settings.GATE_7_MIN_BUY_SELL_RATIO
            if not scored.gate_7_buy_sell_ratio:
                return self._fail_record(scored, f"Gate 7 (Micro: Buy/Sell Ratio {record.t0_buy_sell_ratio:.2f} < {settings.GATE_7_MIN_BUY_SELL_RATIO})", "Tier 3", gates_passed)
        else: # Graduate Mode
            scored.gate_7_buy_sell_ratio = (record.t0_buy_sell_ratio >= settings.GATE_7_MIN_BUY_SELL_RATIO) and (record.t0_buy_sell_ratio <= settings.MODE_GRAD_MAX_BUY_SELL_RATIO)
            if not scored.gate_7_buy_sell_ratio:
                return self._fail_record(scored, f"Gate 7 (Graduate: Buy/Sell Ratio {record.t0_buy_sell_ratio:.2f} outside {settings.GATE_7_MIN_BUY_SELL_RATIO}-{settings.MODE_GRAD_MAX_BUY_SELL_RATIO})", "Tier 3", gates_passed)
        gates_passed += 1

        # Gate 8: Single wallet <= 25% of window volume
        if not record.t0_forensics_collected:
            scored.gate_8_single_wallet_vol = None  # SKIPPED
        else:
            scored.gate_8_single_wallet_vol = record.t0_single_wallet_vol_pct <= settings.GATE_8_MAX_SINGLE_WALLET_VOL_PCT
            if not scored.gate_8_single_wallet_vol:
                return self._fail_record(scored, f"Gate 8 (Whale Vol {record.t0_single_wallet_vol_pct}% > {settings.GATE_8_MAX_SINGLE_WALLET_VOL_PCT}%)", "Tier 3", gates_passed)
        gates_passed += 1

        # Gate 9: Liquidity/mcap ratio (Mode-specific)
        scored.gate_9_liq_mcap_ratio = pass_ratio
        if not scored.gate_9_liq_mcap_ratio:
            return self._fail_record(scored, f"Gate 9 ({mode_name}: Liq/Mcap Ratio {ratio:.3f} outside {min_ratio}-{max_ratio})", "Tier 3", gates_passed)
        gates_passed += 1

        # Gate 10: Unique buyers >= 20 in window
        if not record.t0_forensics_collected:
            scored.gate_10_unique_buyers = None  # SKIPPED
        else:
            scored.gate_10_unique_buyers = record.t0_unique_buyers >= settings.GATE_10_MIN_UNIQUE_BUYERS
            if not scored.gate_10_unique_buyers:
                return self._fail_record(scored, f"Gate 10 (Unique Buyers {record.t0_unique_buyers} < {settings.GATE_10_MIN_UNIQUE_BUYERS})", "Tier 3", gates_passed)
        gates_passed += 1

        # Gate 13: Volume/tx sanity (check that volume isn't 0 when buy ratio > 1)
        # Spec v2: Median buy size > 0.05 SOL ($7.5) and churning volume < 25%
        t0_median_buy_usd = getattr(record, 't0_median_buy_size_usd', 0.0)
        t0_churn_volume_usd = getattr(record, 't0_churn_volume_usd', 0.0)
        t0_volume_usd_15m = getattr(record, 't0_volume_usd_15m', 0.0)
        
        if not record.t0_forensics_collected:
            scored.gate_13_volume_sanity = None  # SKIPPED
        else:
            scored.gate_13_volume_sanity = True
            if t0_median_buy_usd < 7.5:
                scored.gate_13_volume_sanity = False
            
            if t0_volume_usd_15m > 0 and (t0_churn_volume_usd / t0_volume_usd_15m) > 0.25:
                scored.gate_13_volume_sanity = False
                
            if not scored.gate_13_volume_sanity:
                return self._fail_record(scored, f"Gate 13 (Volume Sanity: Median Buy ${t0_median_buy_usd:.2f})", "Tier 4", gates_passed)
        gates_passed += 1

        # --- Tier 4a/4b: Funding Heuristic & Forensic Trace ---

        # Gate 12: No funding-source clustering (pool_slot close to creator_funding_slot)
        # A difference of < 100 slots (approx 40 seconds) indicates highly automated bot behavior
        pool_slot = getattr(record, 'pool_slot', 0)
        creator_funding_slot = getattr(record, 'creator_funding_slot', 0)
        
        # We only evaluate Gate 12 if slot data was actually collected (> 0)
        if pool_slot == 0 and creator_funding_slot == 0:
            scored.gate_12_funding_cluster = None  # SKIPPED
        else:
            scored.gate_12_funding_cluster = True
            if abs(pool_slot - creator_funding_slot) < 100:
                scored.gate_12_funding_cluster = False
                    
            if not scored.gate_12_funding_cluster:
                return self._fail_record(scored, "Gate 12 (Funding Source Sybil Cluster Detected)", "Tier 4a", gates_passed)
        gates_passed += 1

        # If we reached here, ALL 14 GATES PASSED!
        scored.passed_all_gates = True
        scored.first_failed_gate = "PASSED (SKIPPED 4 FORENSICS)" if not record.t0_forensics_collected else None
        scored.first_failed_tier = None
        scored.total_gates_passed = gates_passed
        return scored

    def _fail_record(self, scored: ScoredTokenRecord, reason: str, tier: str, gates_passed: int) -> ScoredTokenRecord:
        """Helper to mark a record as failed and record short-circuit metadata."""
        scored.passed_all_gates = False
        scored.first_failed_gate = reason
        scored.first_failed_tier = tier
        scored.total_gates_passed = gates_passed
        return scored

    def generate_calibration_report(self) -> str:
        """Generate a summarized text report of the pipeline's performance."""
        if not self.scored_records:
            return "No scored records available."

        df = pd.DataFrame([r.model_dump() for r in self.scored_records])
        total_tokens = len(df)
        passed_df = df[df["passed_all_gates"] == True]
        failed_df = df[df["passed_all_gates"] == False]
        partial_pass_df = passed_df[passed_df["t0_forensics_collected"] == False] if "t0_forensics_collected" in passed_df.columns else pd.DataFrame()

        # Cross-tabulate Outcome Label vs Pipeline Pass/Fail
        def _decision_label(row):
            if row["passed_all_gates"]:
                return "Passed All 14 Gates" if row.get("t0_forensics_collected", True) else "Passed (SKIPPED 4 Forensics)"
            return "Failed >= 1 Gate (REJECTED)"
            
        df["decision_label"] = df.apply(_decision_label, axis=1)
        cross_tab = pd.crosstab(
            df["decision_label"],
            df["outcome_label"],
            margins=True,
            margins_name="Total",
        )

        # Failure Breakdown by Gate
        failure_counts = failed_df["first_failed_gate"].value_counts().reset_index()
        failure_counts.columns = ["Failed Gate (Short-Circuit Reason)", "Tokens Rejected"]
        failure_counts["% of Rejected"] = (failure_counts["Tokens Rejected"] / len(failed_df) * 100).round(1) if len(failed_df) > 0 else 0.0

        report_lines = [
            "=" * 80,
            " [REPORT] LOW-MC TOKEN SNIPER BOT (v2) — GATE CALIBRATION & BACKTEST REPORT",
            "=" * 80,
            f"Total Historical Tokens Analyzed : {total_tokens}",
            f"Tokens Passing All 14 Gates      : {len(passed_df)} ({len(passed_df)/total_tokens*100:.1f}%)" + (f" [Includes {len(partial_pass_df)} partial passes]" if len(partial_pass_df) > 0 else ""),
            f"Tokens Rejected by Pipeline      : {len(failed_df)} ({len(failed_df)/total_tokens*100:.1f}%)",
            "-" * 80,
            " [CROSS-TAB] SECTION 9 CROSS-TABULATION: PIPELINE DECISION vs. ACTUAL OUTCOME",
            "-" * 80,
            cross_tab.to_string(),
            "-" * 80,
            " [REJECTIONS] SHORT-CIRCUIT REJECTION BREAKDOWN (Where Did Candidates Fail?)",
            "-" * 80,
            failure_counts.to_string(index=False),
            "=" * 80,
            " [VERDICT] CALIBRATION VERDICT & GUIDANCE:",
        ]

        # Automated verdict analysis per Section 9 rules
        passed_rugs = len(passed_df[passed_df["outcome_label"] == "Rug / dead"])
        passed_winners = len(passed_df[passed_df["outcome_label"] == "Winner"])
        
        # Calculate Winner Retention Rates properly by architectural bands
        all_winners = df[df["outcome_label"] == "Winner"]
        
        def get_subset(df, min_val, max_val):
            if max_val == float('inf'):
                return df[df["t0_mcap_usd"] >= min_val]
            return df[(df["t0_mcap_usd"] >= min_val) & (df["t0_mcap_usd"] < max_val)]

        bands = [
            ("Micro Mode ($5k-$30k)", 5000, 30000),
            ("Death Zone ($30k-$100k)", 30000, 100000),
            ("Gap ($100k-$150k)", 100000, settings.MODE_GRAD_MIN_MCAP_USD),
            (f"Graduate Mode (>={settings.MODE_GRAD_MIN_MCAP_USD:,.0f})", settings.MODE_GRAD_MIN_MCAP_USD, float('inf'))
        ]

        report_lines.extend([
            " [METRICS] ORGANIC WINNER RETENTION",
            "-" * 80
        ])

        for label, b_min, b_max in bands:
            w_total = len(get_subset(all_winners, b_min, b_max))
            w_passed = len(get_subset(passed_df[passed_df["outcome_label"] == "Winner"], b_min, b_max))
            retention = (w_passed / w_total * 100) if w_total > 0 else 0.0
            report_lines.append(f"{label:28s} : {retention:5.1f}% ({w_passed} / {w_total} passed)")

        report_lines.extend([
            "=" * 80,
            " [VERDICT] CALIBRATION VERDICT & GUIDANCE:"
        ])

        if len(passed_df) == 0:
            report_lines.append("  [WARN] ZERO TOKENS PASSED: Your cutoff thresholds are currently TOO STRICT.")
            report_lines.append("     Recommendation: Loosen Gate 6 (Holder Count), Gate 11a (Mcap Band), or Gate 14 (Age Window).")
        elif passed_rugs > 0:
            rug_rate = (passed_rugs / len(passed_df)) * 100
            report_lines.append(f"  [WARN] RUG LEAKAGE DETECTED: {rug_rate:.1f}% of alerted tokens turned out to be rugs!")
            report_lines.append("     Recommendation: Tighten Gate 4 (Top 10 Holder %), Gate 7 (Buy/Sell Ratio), or Gate 8 (Whale Vol).")
        else:
            report_lines.append(f"  [OK] ZERO RUG RATE ACHIEVED! 0% of alerted tokens rugged. ({passed_winners} confirmed Winners).")
            report_lines.append("     The architecture is working as intended on this dataset.")

        report_lines.append("=" * 80)
        report_str = "\n".join(report_lines)
        return report_str

    def export_scored_dataset(self, filename_prefix: str = "solana_scored_tokens") -> tuple[str, str]:
        """Export enriched scored dataset to CSV and JSON."""
        if not self.scored_records:
            return "", ""

        df = pd.DataFrame([r.model_dump() for r in self.scored_records])
        timestamp_str = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d_%H%M%S")
        
        csv_path = settings.PROCESSED_DATA_DIR / f"{filename_prefix}_{timestamp_str}.csv"
        json_path = settings.PROCESSED_DATA_DIR / f"{filename_prefix}_{timestamp_str}.json"
        log_path = settings.LOG_DIR / f"calibration_report_{timestamp_str}.log"

        df.to_csv(csv_path, index=False)
        df.to_json(json_path, orient="records", indent=2)

        report = self.generate_calibration_report()
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"Saved scored dataset to:\n  - CSV: {csv_path}\n  - JSON: {json_path}\n  - Report Log: {log_path}")
        return str(csv_path), str(json_path)
