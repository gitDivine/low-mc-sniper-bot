# Low-Market-Cap Token Sniper Bot — Behavioral Rules & Instructions

## 1. Core Principles & Philosophy
- **Zero-Cost & Free-Tier First:** All architecture, API polling, and data harvesting must be designed to run within free-tier quotas (e.g., DexScreener, GeckoTerminal, Birdeye free tiers, Oracle Cloud free-tier VM).
- **Strict Gating Over Weighted Scoring:** Never implement point-based or weighted scoring for token safety. A token must pass 100% of the defined safety and quality gates. Partial credit is not permitted.
- **Short-Circuit Evaluation:** Order all gate evaluations strictly from lowest computational/financial cost (RPC queries) to highest cost (forensic graph tracing). Stop evaluation immediately on the first failed gate.
- **Auto-Fail on Unverifiable Data:** If an API or indexer cannot verify a required gate (e.g., LP lock status on a new L2), the token must automatically FAIL that gate. Never default to pass or require manual intervention for unverified gates.
- **Verify Before Live Deployment:** Never deploy live scanning rules without validating cutoff thresholds against historical T0 vs. T-final dataset distributions.

---

## 2. Coding Standards
- **Language:** Python 3.12+ with strict type hints (`typing` / `pydantic`).
- **Async & Networking:** Use `asyncio` and `httpx` for all network communications. Implement exponential backoff, retry logic (`tenacity` or custom wrappers), and strict token rate-limit buckets.
- **Data Serialization:** Use `pandas` for tabular dataset processing and export clean CSV/JSON artifacts with standardized timestamps (UTC ISO 8601 or Unix seconds).
- **Error Handling:** Handle API 429 (Rate Limit) and 5xx errors gracefully without crashing the harvester loop. Log all network anomalies with clear context.
