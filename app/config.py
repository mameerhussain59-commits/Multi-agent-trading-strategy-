from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file='.env',extra='ignore')
    app_name:str='Multi-Agent Crypto Trader'
    trading_mode:str='paper'
    mrnasdog_url:str='https://mrnasdog.com/'
    mrnasdog_sitemap_url:str='https://mrnasdog.com/sitemap.xml'
    max_research_pages:int=120
    coingecko_api_key:str|None=None
    request_timeout:float=15.0
    max_data_age_seconds:int=120
    account_equity_usd:float=10000.0
    risk_per_trade_pct:float=0.5
    max_position_pct:float=10.0
    min_signal_score:float=65.0
    min_liquidity_usd:float=250000.0
    max_spread_pct:float=0.50
    db_path:str='data/trader.db'
    dry_run:bool=True
    live_trading_enabled:bool=False
    binance_api_key:str|None=None
    binance_api_secret:str|None=None
    binance_base_url:str='https://api.binance.com'
settings=Settings()
