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
*   **Shadow Mode Runner:** Built, integrated, and verified! (`src/shadow/runner.py` and `run_shadow.py`).
*   **Rate Limiting:** Added dedicated GeckoTerminal rate-limiter (0.4 req/s = 24 req/min) in `src/data_puller/api_client.py` to prevent 429 quota exhaustion when left online 24/7 on a VPS.
*   **On-Chain T0 Gate Checks:** Real-time RPC checks for LP lock/burn (Gate 1), true T0 Top 10 holder % (Gate 4), true T0 Dev wallet % (Gate 5), Liq/MCap ratio (Gate 9), and Token-2022 security extensions (Gate 11a/11b).
*   **Persistence:** Data stored continuously in `data/shadow/pending_tokens.json` and `data/shadow/resolved_tokens.csv`.
*   **Next Focus:** Running Shadow Runner for 24–48 hours to collect a live dataset of 100–300+ resolved tokens with true launch-time gate snapshots.

---

## Latest Summary
We completed the **Shadow Mode Runner** module (`src/shadow/runner.py` and `run_shadow.py`). It monitors live pool launches via GeckoTerminal, executes immediate on-chain RPC calls at launch to capture true T0 holder/dev percentages and LP lock status, queues pending tokens in `data/shadow/pending_tokens.json`, and evaluates 24h ROI outcomes into `data/shadow/resolved_tokens.csv`. We also added dedicated rate limiting to `api_client.py` (capped at 24 req/min for GeckoTerminal and 240 req/min for Helius RPC) to guarantee zero 429 errors during 24/7 long-term operation on VPS servers.

---

## Change Log
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
