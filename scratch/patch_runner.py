import re

with open("src/shadow/runner.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """                logger.info(f"Discovered fresh pool: {symbol} ({pool_address}) | Price: ${price_usd:.6f} | Liq: ${liquidity_usd:,.0f} | MCap: ${mcap_usd:,.0f}")

                # Perform Real-Time T0 Gate Checks via On-Chain RPC
                snapshot = await self._capture_t0_snapshot(
                    pool_address=pool_address,
                    token_address=token_address,
                    symbol=symbol,
                    price_usd=price_usd,
                    liquidity_usd=liquidity_usd,
                    mcap_usd=mcap_usd,
                    vol_15m=vol_15m,
                    age_hours=age_hours,
                    has_rtl_scam=has_rtl_scam,
                )

                if snapshot.get("status") == "DROPPED":
                    self.seen_pools.add(pool_address)
                    self.resolved_tokens.append(snapshot)
                    self._save_resolved_tokens()
                    self._save_seen_pools()
                    continue

                self.seen_pools.add(pool_address)
                self.pending_tokens[pool_address] = snapshot
                new_count += 1

                self._save_seen_pools()
                self._save_pending_tokens()"""

replacement = """                logger.info(f"Discovered fresh pool: {symbol} ({pool_address}) | Queuing for 15m maturity...")
                
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
                self._save_waiting_t0_tokens()"""

if target in content:
    content = content.replace(target, replacement)
    with open("src/shadow/runner.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced discover logic successfully.")
else:
    print("Target not found.")

