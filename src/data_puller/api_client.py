"""Asynchronous HTTP client with rate limiting and retry logic for free-tier APIs."""
import asyncio
import logging
import time
from typing import Any, Optional
import httpx
import base64
import base58
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple asynchronous token-bucket / interval rate limiter to prevent 429 quota exhaustion."""

    def __init__(self, calls_per_second: float):
        self.interval = 1.0 / calls_per_second if calls_per_second > 0 else 0.0
        self.last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until enough time has passed since the last API request."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_call
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self.last_call = time.monotonic()


class AsyncAPIClient:
    """Robust async API client for DexScreener, GeckoTerminal, Birdeye, and Helius."""

    def __init__(self):
        self.rate_limiter = RateLimiter(settings.RATE_LIMIT_CALLS_PER_SECOND)
        self.gecko_rate_limiter = RateLimiter(0.4) # 24 calls/min max for GeckoTerminal free tier
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 LowMCSniperBot/2.0",
            "Accept": "application/json",
        }
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or initialize the underlying httpx AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS),
                limits=httpx.Limits(max_connections=settings.MAX_CONCURRENT_REQUESTS),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client gracefully."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False, # Return None if all retries fail instead of crashing
    )
    async def _get(self, url: str, params: Optional[dict[str, Any]] = None, custom_headers: Optional[dict[str, str]] = None) -> Optional[dict[str, Any] | list[Any]]:
        """Internal GET request wrapper with rate limiting and exponential backoff retry."""
        if "geckoterminal" in url:
            await self.gecko_rate_limiter.acquire()
        else:
            await self.rate_limiter.acquire()

        client = await self.get_client()
        
        headers = {**self.headers, **(custom_headers or {})}
        logger.debug(f"GET {url} | params={params}")
        
        response = await client.get(url, params=params, headers=headers)
        
        if response.status_code == 404:
            logger.warning(f"Resource not found (404): {url}")
            return None
        elif response.status_code == 429:
            logger.warning(f"Rate limited (429) on {url}. Triggering retry backoff...")
            response.raise_for_status()
        elif response.status_code >= 500:
            logger.warning(f"Server error ({response.status_code}) on {url}. Triggering retry backoff...")
            response.raise_for_status()

        try:
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to decode JSON from {url}: {e}")
            return None

    # --- Helius Endpoints ---
    async def fetch_helius_historical_swaps(self, pool_address: str, launch_timestamp: int) -> list[dict]:
        """
        Paginate backward through Helius API to fetch all SWAP transactions from NOW until launch_timestamp.
        Uses the provided Helius API key.
        """
        api_key = getattr(settings, "HELIUS_API_KEY", "0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6")
        url = f"https://api.helius.xyz/v0/addresses/{pool_address}/transactions"
        all_swaps = []
        before_sig = None
        
        # Max pages to prevent infinite loops on mega-winners
        # We use 40 pages (up to 4000 swaps) to ensure we reach T0 for most tokens within a 1-4 hour age.
        MAX_PAGES = 40
        
        for page in range(MAX_PAGES):
            params = {"api-key": api_key, "type": "SWAP"}
            if before_sig:
                params["before"] = before_sig
                
            data = await self._get(url, params=params)
            if not data:
                break
                
            all_swaps.extend(data)
            before_sig = data[-1]["signature"]
            oldest_timestamp = data[-1]["timestamp"]
            
            logger.info(f"Helius pagination: fetched {len(all_swaps)} total swaps, oldest timestamp {oldest_timestamp}")
            
            if oldest_timestamp <= launch_timestamp:
                break
                
        return all_swaps

    # --- DexScreener Endpoints ---

    async def fetch_dexscreener_tokens(self, token_addresses: list[str]) -> list[dict[str, Any]]:
        if not token_addresses:
            return []
        joined = ",".join(token_addresses[:30])
        url = f"{settings.DEXSCREENER_BASE_URL}/tokens/{joined}"
        data = await self._get(url)
        if isinstance(data, dict):
            return data.get("pairs", []) or []
        return []

    async def fetch_dexscreener_search(self, query: str) -> list[dict[str, Any]]:
        url = f"{settings.DEXSCREENER_BASE_URL}/search"
        data = await self._get(url, params={"q": query})
        if isinstance(data, dict):
            return data.get("pairs", []) or []
        return []

    async def fetch_dexscreener_latest_token_profiles(self) -> list[dict[str, Any]]:
        url = f"{settings.DEXSCREENER_BASE_URL}/token-profiles/latest/v1"
        data = await self._get(url)
        if isinstance(data, list):
            return data
        return []

    # --- GeckoTerminal Endpoints ---

    async def fetch_geckoterminal_new_pools(self, network: str = "solana", page: int = 1) -> list[dict[str, Any]]:
        url = f"{settings.GECKOTERMINAL_BASE_URL}/networks/{network}/new_pools"
        try:
            data = await self._get(url, params={"page": page})
            if isinstance(data, dict) and "data" in data:
                return data["data"]
        except Exception as e:
            logger.warning(f"Error fetching new pools from GeckoTerminal: {e}")
        return []

    async def fetch_geckoterminal_pool(self, network: str, pool_address: str) -> Optional[dict[str, Any]]:
        url = f"{settings.GECKOTERMINAL_BASE_URL}/networks/{network}/pools/{pool_address}"
        try:
            data = await self._get(url)
            if isinstance(data, dict) and "data" in data:
                return data["data"]
        except Exception as e:
            logger.warning(f"Error fetching pool {pool_address} from GeckoTerminal: {e}")
        return None

    async def fetch_geckoterminal_ohlcv(self, network: str, pool_address: str, resolution: str = "minute", before_timestamp: Optional[int] = None) -> list[Any]:
        """
        Fetches OHLCV data for a pool from GeckoTerminal.
        Returns a list of candles (list of [timestamp, open, high, low, close, volume]).
        resolution can be 'minute', 'hour', or 'day'.
        """
        url = f"{settings.GECKOTERMINAL_BASE_URL}/networks/{network}/pools/{pool_address}/ohlcv/{resolution}"
        params = {"aggregate": 1, "limit": 100}
        if before_timestamp:
            params["before_timestamp"] = before_timestamp
            
        try:
            data = await self._get(url, params=params)
            if isinstance(data, dict) and "data" in data:
                return data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
        except Exception as e:
            logger.warning(f"Error fetching OHLCV for pool {pool_address} from GeckoTerminal: {e}")
        return []

    # --- Free Public Solana RPC Endpoints (Gates 1, 4, 5) ---

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def fetch_solana_token_supply(self, token_mint: str) -> Optional[float]:
        helius_rpc = f"https://mainnet.helius-rpc.com/?api-key={getattr(settings, 'HELIUS_API_KEY', '0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6')}"
        rpc_urls = [
            helius_rpc,
            "https://solana-rpc.publicnode.com",
            "https://api.mainnet-beta.solana.com",
        ]
        await self.rate_limiter.acquire()
        client = await self.get_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenSupply",
            "params": [token_mint]
        }
        for url in rpc_urls:
            try:
                res = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if res.status_code != 200:
                    continue
                data = res.json()
                val = data.get("result", {}).get("value", {})
                ui_amount = val.get("uiAmount")
                if ui_amount is not None:
                    return float(ui_amount)
            except Exception:
                continue
        return None

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def fetch_solana_token_largest_accounts(self, token_mint: str) -> list[dict[str, Any]]:
        helius_rpc = f"https://mainnet.helius-rpc.com/?api-key={getattr(settings, 'HELIUS_API_KEY', '0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6')}"
        rpc_urls = [
            helius_rpc,
            "https://solana-rpc.publicnode.com",
            "https://api.mainnet-beta.solana.com",
        ]
        await self.rate_limiter.acquire()
        client = await self.get_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenLargestAccounts",
            "params": [token_mint]
        }
        for url in rpc_urls:
            try:
                res = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if res.status_code != 200:
                    continue
                data = res.json()
                accounts = data.get("result", {}).get("value", [])
                results = []
                for acc in accounts:
                    ui_val = acc.get("uiAmount")
                    if ui_val is not None:
                        results.append({"address": acc.get("address", ""), "uiAmount": float(ui_val)})
                if results:
                    return results
            except Exception:
                continue
        return []

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def fetch_pool_lp_mint(self, pool_address: str) -> Optional[str]:
        """
        Fetches the pool account data, verifies it is a Raydium AMM v4 or CPMM pool,
        and decodes the LP mint address from the correct offset.
        Returns the LP Mint address as a base58 string, or None if unsupported or invalid.
        """
        helius_rpc = f"https://mainnet.helius-rpc.com/?api-key={getattr(settings, 'HELIUS_API_KEY', '0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6')}"
        rpc_urls = [
            helius_rpc,
            "https://solana-rpc.publicnode.com",
            "https://api.mainnet-beta.solana.com",
        ]
        await self.rate_limiter.acquire()
        client = await self.get_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                pool_address,
                {"encoding": "base64"}
            ]
        }
        for url in rpc_urls:
            try:
                res = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if res.status_code != 200:
                    continue
                data = res.json()
                acc_info = data.get("result", {}).get("value")
                if not acc_info:
                    continue
                
                owner = acc_info.get("owner")
                b64_data = acc_info.get("data", [""])[0]
                raw_data = base64.b64decode(b64_data)
                
                if owner == "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": # Raydium v4
                    if len(raw_data) < 496:
                        return None
                    pk_bytes = raw_data[464:496]
                    return base58.b58encode(pk_bytes).decode('ascii')
                elif owner == "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": # Raydium CPMM
                    if len(raw_data) < 168:
                        return None
                    pk_bytes = raw_data[136:168]
                    return base58.b58encode(pk_bytes).decode('ascii')
                elif owner in ("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG", "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"):
                    # Pump.fun bonding curve or Raydium launchpad: liquidity is program-locked by protocol design
                    return "PROGRAM_LOCKED"
                else:
                    logger.warning(f"Pool {pool_address} has unsupported owner: {owner}")
                    return "PROGRAM_LOCKED" # Treat generic DEX pools as program locked for historical harvest fallback
            except Exception as e:
                logger.error(f"Error fetching LP mint for pool {pool_address}: {e}")
                continue
        return None

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def fetch_token_account_info(self, token_mint: str) -> Optional[dict[str, Any]]:
        """
        Fetches the account info for a token mint, returning its owner and data.
        Useful for determining if a token is a standard SPL token or a Token-2022 token,
        and for parsing extensions.
        """
        helius_rpc = f"https://mainnet.helius-rpc.com/?api-key={getattr(settings, 'HELIUS_API_KEY', '0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6')}"
        rpc_urls = [
            helius_rpc,
            "https://solana-rpc.publicnode.com",
            "https://api.mainnet-beta.solana.com",
        ]
        await self.rate_limiter.acquire()
        client = await self.get_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                token_mint,
                {"encoding": "base64"}
            ]
        }
        for url in rpc_urls:
            try:
                res = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if res.status_code != 200:
                    continue
                data = res.json()
                acc_info = data.get("result", {}).get("value")
                if not acc_info:
                    continue
                return acc_info
            except Exception as e:
                logger.error(f"Error fetching token account info for {token_mint}: {e}")
                continue
        return None


api_client = AsyncAPIClient()
