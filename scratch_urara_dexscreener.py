import requests
import json

def check_urara():
    url = "https://api.dexscreener.com/latest/dex/pairs/solana/3xJ6QBzGVa8Q8hjRZ83HihNfh8Wt7Gpc1tVvTPkSxmDs"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        if data.get('pairs'):
            pair = data['pairs'][0]
            print(f"Price: {pair.get('priceUsd')}")
            print(f"Liquidity: {pair.get('liquidity', {}).get('usd')}")
            print(f"FDV: {pair.get('fdv')}")
            print(f"Volume 24h: {pair.get('volume', {}).get('h24')}")
            print(f"Age ms: {pair.get('pairCreatedAt')}")
            
if __name__ == "__main__":
    check_urara()
