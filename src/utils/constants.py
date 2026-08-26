"""
Constants and static lists used across the low-mc-sniper-bot.
"""

# Known Solana Hot Wallets for Centralized Exchanges and prominent services
# If a creator wallet is funded by one of these, we skip clustering based on the funder wallet
# since thousands of unrelated users withdraw from these same addresses.
KNOWN_CEX_WALLETS = {
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9", # Binance (Binance 1)
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", # Binance (Binance 2)
    "8WHYHVhxMGe47uWDDVLSf4zBA4C2ctVhvJvsHUzTuC4e", # Binance (Binance 3)
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61L5JPRX2X789i4", # Coinbase
    "2Q722KfsyNDnK9E9z4Rvyx41Z7mUStzJ5g7W32H8G3G4", # Coinbase
    "BmJt7eG2B9R673d32zC7mD5YxWkC7sC5rV4W6W2P3eJ6", # Kraken
    "DsuZFXDTDAigQaPvvjCPjRehycob7yPPRL5m1o48P1hE", # Kraken / Kucoin
    "GLGQ3yip9M47SekroDQPcjsBxirwKa6G8kbuhGTiYH6G", # OKX
    "5PAhG5T2vL1XyW6o2X4z7tM8YyJ4T5xVbT3N3A6H8G6B", # OKX
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1", # Raydium Authority / Fee
    "AC5RDfQFmDS1deWZos921FCqjzNdUdr4LzM3Lq4M62k3", # Bybit
}
