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
- **2026-08-12** - **IMPORTANT** - Pivoted Gate 6 from the inaccurate `makers` proxy to a true on-chain holder count using Helius DAS. Implemented an early-exit optimization (`limit=100`) to strictly protect the 2 req/s DAS rate limit while preserving full analytical detail. Restructured the T0 pipeline with a "fail-loud" architecture that explicitly tags dropped tokens with a `drop_reason` field and saves them directly to the resolved dataset, eliminating ambiguous data-loss gaps.
- **2026-08-10** - **IMPORTANT** - Identified and quantified a ~27% undercount limitation in GeckoTerminal's pool discovery via RPC cross-checking. Calibrated Gate 4 to 25.0% and Gate 5 to 5.0% based on the cleaned organic sample. Unified `Winner` outcome labeling in the Shadow Runner to strictly enforce these gate cutoffs at T0, eliminating wash-traded scam bias from downstream analytics.
- **2026-08-07** - **CRITICAL** - Implemented Shadow Mode Runner (`src/shadow/runner.py`, `run_shadow.py`). Added dedicated 0.4 req/s GeckoTerminal rate limiter to `api_client.py` for rate-limit safe long-term VPS monitoring.
- **2026-08-06** - **IMPORTANT** - Fixed historical outcome labeler in `harvester.py` to use ROI-only logic, fixing the zero-liquidity stub bug that caused false "Rug/dead" labels.
- **2026-08-06** - **IMPORTANT** - Harvested 40 historical Solana token pools using OHLCV lookups for T0 and T24h prices to bypass Helius swap pagination bottlenecks.
- **2026-07-28** - **IMPORTANT** - Built and ran Script 2 Backtest Engine (`src/backtester/run_backtest.py`) against 159-token multi-chain historical dataset.
- **2026-07-27** - **IMPORTANT** - Initialized project structure and governance files for Low-Market-Cap Token Sniper Bot v2 (`low-mc-sniper-bot`).

---

## Pending Tasks
- [x] Implement robust async API client (`src/data_puller/api_client.py`) with rate limiting and exponential backoff.
- [x] Implement historical pair harvester (`src/data_puller/harvester.py`) for Solana with T0 snapshot capture and T-final labeling.
- [x] Build Script 2 (`src/evaluator/scorer.py`) for offline 14-gate evaluation and cutoff calibration.
- [x] Build Shadow Runner (`src/shadow/runner.py` & `run_shadow.py`) for real-time live discovery and T0 gate snapshotting.
- [ ] Run Shadow Runner on VPS for 24-48h to collect live T0 calibration dataset (~100-300 resolved tokens).
- [ ] Auto-calibrate Gate 4 (Top 10 %), Gate 5 (Dev %), and Gate 9 (Liq/MCap) using resolved shadow dataset.
- [ ] Build Script 3 (Live Snipe Engine) with WebSocket execution for real-time trading/alerting.

---

## Known Issues
*   *None currently reported.*

---

## Decisions & Reasoning
*   **Shadow Mode over Historical RPC Holder Queries:** On-chain holder queries (`getTokenLargestAccounts`) return current holder distributions, which drift after tokens rug. Running in shadow mode captures true launch-time (T0) holder distributions in real time.
*   **Dedicated Per-API Rate Limiting:** GeckoTerminal free tier has a 30 req/min limit while Helius RPC permits 600 req/min. Separating API rate limiters in `api_client.py` ensures maximum speed for RPC calls without triggering 429 blocks on GeckoTerminal.
*   **Discovery Methodology (GeckoTerminal vs On-Chain):** Pool discovery uses GeckoTerminal's `/networks/solana/new_pools` endpoint. This provides valuable multi-DEX coverage without requiring bespoke indexers for every AMM protocol. **Measured Limitation:** An RPC cross-check of Pump.fun migrations to Raydium over a 4-hour window revealed that GT is lossy: it only captured ~140 pools versus the 191 real on-chain migrations (a ~27% undercount), and a random spot-check confirmed GT completely drops/fails to index ~30% of valid pools. We mitigate GT's 10-page maximum pagination cliff by running the Shadow Runner with a fast 5-minute poll interval, ensuring we capture everything GT *does* expose. However, the ~25-30% baseline undercount of true market volume is a known, unresolved limitation of relying on GT for discovery.
