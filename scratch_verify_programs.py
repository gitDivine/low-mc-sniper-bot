import urllib.request
import json
import urllib.error

def check_program(address):
    url = "https://api.mainnet-beta.solana.com"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [
            address,
            {"encoding": "jsonParsed"}
        ]
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"--- {address} ---")
            info = data.get('result', {}).get('value')
            if info:
                print(f"Executable: {info.get('executable')}")
                print(f"Owner: {info.get('owner')}")
            else:
                print("Not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_program("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
    check_program("cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG")
    check_program("pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
