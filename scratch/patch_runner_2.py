import re

with open("src/shadow/runner.py", "r", encoding="utf-8") as f:
    content = f.read()

method_str = """
    async def process_waiting_t0_pools(self) -> int:
        \"\"\"Checks waiting pools and evaluates them exactly when they cross 15m maturity.\"\"\"
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
                
                attributes = pool_data.get("data", {}).get("attributes", {})
                price_usd = float(attributes.get("base_token_price_usd") or 0.0)
                liquidity_usd = float(attributes.get("reserve_in_usd") or 0.0)
                mcap_usd = float(attributes.get("fdv_usd") or 0.0)
                
                volume_dict = attributes.get("volume_usd", {})
                vol_15m = float(volume_dict.get("m5", 0.0) or volume_dict.get("h1", 0.0) or 0.0)
                
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
"""

if "def process_waiting_t0_pools" not in content:
    # Insert before _capture_t0_snapshot
    target_pos = content.find("    async def _capture_t0_snapshot")
    content = content[:target_pos] + method_str + "\n" + content[target_pos:]

# Now patch run_loop
run_loop_target = """                # 1. Discover fresh pools & take T0 snapshot
                try:
                    await self.discover_and_snapshot(pages=10)
                except Exception as e:
                    logger.error(f"Error during discovery pass: {e}")

                # 2. Check for matured tokens & compute ROI outcomes"""

run_loop_repl = """                # 1. Discover fresh pools & queue for 15m maturity
                try:
                    await self.discover_and_snapshot(pages=10)
                except Exception as e:
                    logger.error(f"Error during discovery pass: {e}")

                # 2. Process waiting pools that reached 15m maturity
                try:
                    await self.process_waiting_t0_pools()
                except Exception as e:
                    logger.error(f"Error processing waiting pools: {e}")

                # 3. Check for 24h matured tokens & compute ROI outcomes"""

if run_loop_target in content:
    content = content.replace(run_loop_target, run_loop_repl)
    
# Update log message in discover_and_snapshot
log_target = 'Captured {new_count} new token T0 snapshots. Total pending: {len(self.pending_tokens)}'
log_repl = 'Discovered {new_count} fresh pools. Total waiting for maturity: {len(self.waiting_t0_tokens)}'
if log_target in content:
    content = content.replace(log_target, log_repl)
    
with open("src/shadow/runner.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched completely.")

