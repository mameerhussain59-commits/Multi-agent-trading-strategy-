from datetime import datetime, timezone
from pydantic import BaseModel, Field

class Token(BaseModel):
    symbol: str
    name: str | None = None
    source: str
    source_score: float | None = None
    source_url: str | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MarketSnapshot(BaseModel):
    symbol: str
    pair: str
    price: float
    change_24h: float = 0
    volume_24h: float = 0
    high_24h: float | None = None
    low_24h: float | None = None
    market_cap: float | None = None
    liquidity_usd: float | None = None
    spread_pct: float | None = None
    exchange: str
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TechnicalSnapshot(BaseModel):
    symbol: str
    timeframe: str
    rsi: float
    ema_fast: float
    ema_slow: float
    atr: float
    trend: str
    momentum_score: float

class TradePlan(BaseModel):
    symbol: str
    side: str = 'LONG'
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward: float
    position_size: float
    risk_usd: float
    score: float
    executable: bool = False
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    mode: str = 'paper'

class ScanResult(BaseModel):
    token: Token
    market: MarketSnapshot
    technical: TechnicalSnapshot
    trade: TradePlan
    data_sources: list[str]
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
