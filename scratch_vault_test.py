import asyncio
from src.data_puller.api_client import api_client

async def test():
    # tokens for testing
    tokens = [
        'DHFSEDzTj7o51Ar8RAD5tS76dcmLU9r7Qpyyhhr2ccKZ', # bCard
        '3YUR6fezkKGAANi65Uqff9PUVVGJeCT1LGYQzeU1BAGS' # HTZ (Flat Dave)
    ]
    for token in tokens:
        accounts = await api_client.fetch_solana_token_largest_accounts(token)
        print(f'\nLargest accounts for {token}:', accounts[:3] if accounts else None)
        
        # check first account
        if accounts:
            client = await api_client.get_client()
            helius_rpc = 'https://mainnet.helius-rpc.com/?api-key=0182f0e1-1ebc-4396-9cc3-9e2443b1e9c6'
            res = await client.post(helius_rpc, json={
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getAccountInfo',
                'params': [accounts[0]['address'], {'encoding': 'jsonParsed'}]
            })
            acc_data = res.json()
            if 'result' in acc_data and acc_data['result']['value']:
                owner = acc_data['result']['value'].get('owner')
                parsed = acc_data['result']['value'].get('data', {}).get('parsed', {}).get('info', {})
                print(f'System owner: {owner}')
                print(f'Parsed authority (wallet): {parsed.get("owner")}')

    await api_client.close()

if __name__ == "__main__":
    asyncio.run(test())
