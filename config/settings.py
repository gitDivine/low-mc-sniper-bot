"""Project settings and gate configuration thresholds for Low-MC Token Sniper Bot."""
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core configuration for data harvesting, backtesting, and gate thresholds."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project Paths
    BASE_DIR: Path = Path(__file__).parent.parent if "__file__" in globals() else Path.cwd()
    RAW_DATA_DIR: Path = Field(default_factory=lambda: Path.cwd() / "data" / "raw")
    PROCESSED_DATA_DIR: Path = Field(default_factory=lambda: Path.cwd() / "data" / "processed")
    LOG_DIR: Path = Field(default_factory=lambda: Path.cwd() / "memory" / "backtest_logs")

    # API Endpoints & Keys
    DEXSCREENER_BASE_URL: str = "https://api.dexscreener.com/latest/dex"
    GECKOTERMINAL_BASE_URL: str = "https://api.geckoterminal.com/api/v2"
    BIRDEYE_BASE_URL: str = "https://public-api.birdeye.so"
    BIRDEYE_API_KEY: Optional[str] = Field(default=None, description="Optional Birdeye API Key for extended historical data")
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, description="Telegram Bot API Token for alerts & heartbeat")
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, description="Telegram Chat ID to receive alerts & data files")

    # Rate Limiting & Networking (Zero-Cost / Free-Tier Friendly)
    MAX_CONCURRENT_REQUESTS: int = 4
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    RATE_LIMIT_CALLS_PER_SECOND: float = 3.5  # Safe margin below DexScreener 300/min limit

    # Historical Harvester Target Window (Section 7, Step 1)
    HISTORICAL_MIN_DAYS_AGO: float = 1.0
    HISTORICAL_MAX_DAYS_AGO: float = 30.0
    TARGET_CHAINS: list[str] = Field(default_factory=lambda: ["solana"])

    # 14-Gate Thresholds (Section 3 Starting Hypotheses)
    GATE_1_LP_LOCK_MIN_DAYS: int = 30
    GATE_4_TOP10_HOLDER_MAX_PCT: float = 25.0
    GATE_5_DEV_WALLET_MAX_PCT: float = 5.0
    GATE_6_MIN_HOLDER_COUNT: int = 50
    GATE_7_MIN_BUY_SELL_RATIO: float = 2.0
    GATE_8_MAX_SINGLE_WALLET_VOL_PCT: float = 25.0
    GATE_9_MIN_LIQ_MCAP_RATIO: float = 0.25
    GATE_10_MIN_UNIQUE_BUYERS: int = 20
    GATE_11A_MIN_MCAP_USD: float = 30_000.0
    GATE_11A_MAX_MCAP_USD: float = 100_000.0
    GATE_11B_MIN_ABSOLUTE_LIQ_USD: float = 10_000.0
    GATE_12_CLUSTER_MAX_WALLETS_SAME_SOURCE: int = 4  # 5+ is a fail
    GATE_12_CLUSTER_WINDOW_SECONDS: int = 60
    GATE_14_MIN_AGE_MINUTES: int = 15
    GATE_14_MAX_AGE_MINUTES: int = 240

    # Outcome Labeling Rules (Section 7, Step 3)
    LABEL_RUG_MAX_PRICE_RETENTION_PCT: float = 10.0  # Down 90%+ is rug/dead
    LABEL_WINNER_MIN_PRICE_MULTIPLIER: float = 3.0   # 3x+ is winner

    def ensure_directories(self) -> None:
        """Create necessary data and log directories if they don't exist."""
        self.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
