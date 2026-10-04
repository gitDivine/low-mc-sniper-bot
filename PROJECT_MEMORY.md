# Project Memory - Low-Market-Cap Token Sniper Bot (v2)

## Project Overview
This project is an automated, zero-cost token sniper and alert system for Solana, BNB Chain, and Robinhood Chain (EVM L2 on Arbitrum). It replaces traditional weighted scoring models with a strict **14-gate pass/fail filter** and a **short-circuit tiered execution pipeline** designed to optimize rate-limited APIs and free-tier infrastructure.

---

## Architecture
The system operates as a two-script architecture with a 4-tier execution pipeline:

### 1. Two-Script & Shadow Runner Separation
*   **Script 1 (Data-Puller):** Harvester that queries DexScreener, GeckoTerminal, and Birdeye APIs to reconstruct historical token snapshots at T0 ($10\text{ min}$ age, $\$30\text{k}-\$100\text{k}$ mcap band) and tracks T-final outcomes ($24\text{h}$ and $7\text{d}$ later). Output: raw dataset (CSV/JSON).
*   **Script 2 (Scoring & Labeling):** Fast offline evaluator that runs the 14-gate pipeline against T0 snapshots and computes outcome labels (Rug/Dead, Flat/Mediocre, Winner) to iteratively tune cutoffs without incurring API costs.
*   **Shadow Runner (`run_shadow.py`):** Real-time shadow monitor with integrated **Telegram Bot Alerts & Document Delivery** (`src/shadow/telegram_bot.py`). Sends startup alerts, hourly heartbeats, interactive inline action buttons (`[ 📊 Get CSV Data ]`, `[ 📈 View Report ]`), and allows instant CSV downloads via `/getdata` or button taps inside Telegram.

### 2. Tiered Execution Pipeline (Short-Circuit on First Fail)
*   **Tier 1 (Smart Contract Triage - Free/Instant RPC):** Gate 1 (LP locked/burned), Gate 2 (Mint/freeze renounced).
*   **Tier 2 (Basic Checks + Honeypot - Low Cost / Indexer APIs):** Gate 3 (Honeypot check via API), Gate 4 (Top 10 holder % $\le 20\%$), Gate 5 (Dev wallet $\le 3\%$), Gate 11a/b (Mcap band & Absolute liquidity floor $\ge \$10\text{k}$), Gate 14 (Time-in-market $15\text{ min} - 4\text{ hr}$).
*   **Tier 3 (Momentum & Wash-Trade Filters - Medium Cost):** Gate 6 (Holder count $\ge 75$), Gate 7 (Buy/sell ratio $\ge 2:1$), Gate 8 (Single wallet window volume $\le 25\%$), Gate 9 (Liq/Mcap ratio $\ge 0.25$), Gate 10 (Unique buyers $\ge 20$), Gate 13 (Volume/tx-count sanity).
*   **Tier 4a (Funding Heuristic - Cheap Pass):** Gate 12 first pass (check first-inbound tx timestamp/address for top holders; flag if 5+ funded from same source within $60\text{s}$ or same block).
*   **Tier 4b (Funding Forensic Trace - Rare High Cost):** Gate 12 full transaction-graph traversal only when Tier 4a is ambiguous.

---

## Current State
*   **Shadow Mode Runner:** Built, integrated, and verified with Telegram bot capabilities (`src/shadow/runner.py`, `src/shadow/telegram_bot.py`, `run_shadow.py`).
*   **Wide-Scope Collection Architecture:** Configured discovery to collect wide-scope raw data ($5k–$500k MCap & $1k+ Liquidity) so un-biased raw data is preserved while Gate 11a/11b spec cutoffs ($30k–$100k MCap) are applied strictly at analysis time.
*   **Data Hygiene & Disambiguation:** Integrated Unicode RTL Impersonation Scam Filter (`\u202e` etc.), dynamic timeframe labels (`24.0h`), and `Symbol (ShortAddress)` format to prevent ticker collisions on-chain.
*   **Rate Limiting:** Added dedicated GeckoTerminal rate-limiter (0.4 req/s = 24 req/min) in `src/data_puller/api_client.py` to prevent 429 quota exhaustion when left online 24/7 on a VPS.

---

## Change Log
- **2026-10-04** - **CRITICAL** - Discovered that a silent `AttributeError` typo (`_make_request` instead of `_get`) in `api_client.py`'s `fetch_rugcheck_report` method caused 100% of tokens to fail Gate 3 (Rugcheck) silently with `data_incomplete_rugcheck` over an entire 7-day batch. The method was trusted via a standalone raw-urllib test script but never exercised via an integration test. Fixed the typo to use `self._get()`.
- **2026-10-04** - **IMPORTANT** - Built `test_smoke_runner.py` as a standing end-to-end integration check. This script intentionally bypasses Gate 9/11 bounds to pull a live token straight through the Gate 3 (Rugcheck) and Gate 12 (RPC) pipeline, asserting that the snapshot completes without exceptions and fields populate correctly. This must now be run as a required pre-push check for any changes to `api_client.py`, `runner.py`, or `scorer.py` to prevent silent structural drift.
- **2026-08-31** - **CRITICAL** - Gate 12 (Sybil Funder) backwards-pagination bug identified and proven fatal. `api_client.fetch_creator_funding_info` attempts to find the genesis transaction by paginating backward, but high-volume tokens generate tens of thousands of failed transactions (bot spam) in their first 15 minutes. Testing on Hyper-Clean Sybil rugs (NINJA, CRYPT, GIPP) proved that **100% of sophisticated Sybil rings hit this pagination wall**. Gate 12 is officially considered **structurally disabled/non-functional** against sophisticated bad actors until a forward-looking extraction pipeline (webhooks/indexer) is built.
- **2026-08-31** - **CRITICAL** - Discovered that Gate 2 (Mint/Freeze renounced) and Gate 3 (Honeypot) have been hardcoded to `True` (passing) since the very beginning of the project's data collection. This means every prior "clean pass" count in Batches 1 through 14 was an overcount, as no token was ever failed for having an active mint/freeze authority or honeypot risk. Both fixed via native RPC base64 layout parsing (Gate 2) and RugCheck API (Gate 3).
- **2026-08-26** - **IMPORTANT** - Fully implemented Gate 12 (Funding Source Sybil Cluster check) with persistent 48h rolling history, CEX wallet bypass, and a strict 2-page pagination fail-safe. Validated that the fail-safe safely skips heavily active >48h-old historical wallets to prevent hanging. Validated that the clustering logic correctly evaluates and passes non-clustered wallets when the funding source *is* successfully retrieved. Note: Since historical testing relies on 48h-old data, the success rate of retrieving the funder (and thus the skip rate of Gate 12) is artificially depressed in backtests. Live T0 data (15 minutes old) is expected to have a significantly lower skip-rate, but this must be explicitly measured in the next batch.
- **2026-08-17** - **CRITICAL** - Implemented the "Two-Mode Architecture" (Micro: $5k-$30k, Graduate: >=$150k) to address mode-dependent blind spots. Calibrated and empirically validated Gates 7, 9, and 11a/11b against historical datasets, observing inverted token behavior across scale. Conducted an interim *logical* pass for Gates 8, 12, and 14; these are treated as structurally sound placeholders but explicitly **not** empirically validated yet, pending live data collection.
- **2026-08-14** - **IMPORTANT** - Updated Gate 6 threshold to `t0_holder_count >= 50` based on Batch 4 48-hour data analysis (Option A). Introduced explicit tracking for "Unindexed Lag" tokens (where DAS returns exactly 0 holders) in `src/evaluator/scorer.py` to separate timing artifacts from genuine low-holder rejections. This enables future retry mechanisms to recover these tokens (which represent ~19% of winners) without diluting the strict cutoff logic.

---

## Pending Tasks
- [x] Implement robust async API client (`src/data_puller/api_client.py`) with rate limiting and exponential backoff.
- [x] Implement historical pair harvester (`src/data_puller/harvester.py`) for Solana with T0 snapshot capture and T-final labeling.
- [x] Build Script 2 (`src/evaluator/scorer.py`) for offline 14-gate evaluation and cutoff calibration.
- [x] Build Shadow Runner (`src/shadow/runner.py` & `run_shadow.py`) for real-time live discovery and T0 gate snapshotting.
- [ ] **IMMEDIATE:** Design a forward-looking extraction pipeline (Webhook vs Paid Indexer) to replace the disabled Gate 12 backward-pagination method. This must be a dedicated architectural pass.
- [ ] Run Shadow Runner on VPS for 24-48h to collect live T0 calibration dataset with full forensic fields (unique buyers, funding slots).
- [ ] Run percentile-by-mode breakdown on Gates 8, 10, 12, 13, and 14 immediately once live data collection provides the forensic fields. Hunt specifically for mode-dependent inversion.
- [ ] Auto-calibrate Gate 4 (Top 10 %), Gate 5 (Dev %), and Gate 9 (Liq/MCap) using resolved shadow dataset.
- [ ] Build Script 3 (Live Snipe Engine) with WebSocket execution for real-time trading/alerting.

---

## Known Issues
*   **Gate 12 Structural Blindspot / Disabled:** Gate 12's RPC-based funder tracing is confirmed structurally unable to resolve high-volume tokens, which includes both genuine winners AND the exact Sybil-ring pattern it was designed to catch (confirmed via GOZMO/CRYPT/NINJA-class tokens). Gate 12 should be considered **non-functional** against sophisticated Sybil rings until a forward-looking capture pipeline is built.
*   **Gate 14 Anchor Time Ambiguity:** The "5-30 minutes" anchor time may not mean the same thing structurally for Graduate vs. Micro tokens. For a Graduate token, if measured from the original bonding curve creation instead of Raydium migration, the token could already be hours old. This must be verified with real timing data.

---

## Decisions & Reasoning
*   **Shadow Mode over Historical RPC Holder Queries:** On-chain holder queries (`getTokenLargestAccounts`) return current holder distributions, which drift after tokens rug. Running in shadow mode captures true launch-time (T0) holder distributions in real time.
*   **Dedicated Per-API Rate Limiting:** GeckoTerminal free tier has a 30 req/min limit while Helius RPC permits 600 req/min. Separating API rate limiters in `api_client.py` ensures maximum speed for RPC calls without triggering 429 blocks on GeckoTerminal.
*   **Discovery Methodology (GeckoTerminal vs On-Chain):** Pool discovery uses GeckoTerminal's `/networks/solana/new_pools` endpoint. This provides valuable multi-DEX coverage without requiring bespoke indexers for every AMM protocol. **Measured Limitation:** An RPC cross-check of Pump.fun migrations to Raydium over a 4-hour window revealed that GT is lossy: it only captured ~140 pools versus the 191 real on-chain migrations (a ~27% undercount), and a random spot-check confirmed GT completely drops/fails to index ~30% of valid pools. We mitigate GT's 10-page maximum pagination cliff by running the Shadow Runner with a fast 5-minute poll interval, ensuring we capture everything GT *does* expose. However, the ~25-30% baseline undercount of true market volume is a known, unresolved limitation of relying on GT for discovery.
