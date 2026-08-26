import urllib.request
import json
import urllib.error

def check_urara2():
    url = "https://api.geckoterminal.com/api/v2/networks/solana/pools/4sxEtjwHENUwxcyDwx2V32xUNigz7BMsTSPS1J2NgzCy"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            attr = data.get('data', {}).get('attributes', {})
            print(f"Name: {attr.get('name')}")
            print(f"Price: {attr.get('base_token_price_usd')}")
            print(f"Liquidity: {attr.get('reserve_in_usd')}")
            print(f"Volume 24h: {attr.get('volume_usd', {}).get('h24')}")
            print(f"Transactions 24h: {attr.get('transactions', {}).get('h24')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")

if __name__ == "__main__":
    check_urara2()
