import asyncio
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import settings
from src.data_puller.api_client import api_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_experiment(duration_minutes=10, retry_delay=60):
    logger.info(f"Starting retry lag experiment for {duration_minutes} minutes...")
    seen_pools = set()
    end_time = asyncio.get_event_loop().time() + duration_minutes * 60
    
    zero_holder_tokens = []
    
    while asyncio.get_event_loop().time() < end_time:
        try:
            pools = await api_client.fetch_geckoterminal_new_pools(network="solana", page=1)
            if not pools:
                await asyncio.sleep(10)
                continue
                
            for pool_data in pools:
                attributes = pool_data.get("attributes", {})
                pool_address = attributes.get("address")
                
                if not pool_address or pool_address in seen_pools:
                    continue
                
                seen_pools.add(pool_address)
                
                relationships = pool_data.get("relationships", {})
                base_token_id = relationships.get("base_token", {}).get("data", {}).get("id", "")
                token_address = base_token_id.replace("solana_", "") if base_token_id else ""
                
                if not token_address:
                    continue
                
                # Check Helius DAS
                logger.info(f"Checking T0 holder count for {token_address}")
                holder_count = await api_client.fetch_helius_das_holder_count(token_address, limit=100)
                
                if holder_count == 0:
                    logger.warning(f"Token {token_address} returned 0 holders! Queueing for retry in {retry_delay}s...")
                    zero_holder_tokens.append(token_address)
                    
                    # Schedule a retry in the background
                    async def retry_task(token):
                        await asyncio.sleep(retry_delay)
                        retry_count = await api_client.fetch_helius_das_holder_count(token, limit=100)
                        logger.info(f"RETRY RESULT for {token} after {retry_delay}s: {retry_count} holders!")
                    
                    asyncio.create_task(retry_task(token_address))
                
                await asyncio.sleep(0.5) # respect rate limit
        except Exception as e:
            logger.error(f"Error: {e}")
            
        await asyncio.sleep(30)
        
    await api_client.close()
    logger.info("Experiment finished.")

if __name__ == "__main__":
    asyncio.run(run_experiment(duration_minutes=3, retry_delay=60))
