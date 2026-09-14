# Multi-Agent Crypto Trading Strategy

A real-data multi-agent crypto research and paper-trading system. **No synthetic prices, fake candles, or fabricated market observations are used.**

## Pipeline

`MrNasdog research discovery -> live exchange market data -> CoinGecko enrichment -> DEX Screener liquidity -> technical agent -> signal agent -> risk agent -> paper execution -> persistent trade log`

### Agents

- **Master Agent**: orchestrates the complete scan.
- **Token Hunter**: reads MrNasdog research pages live and accepts only pages exposing an explicit 0-10 score.
- **Market Data Agent**: Binance public API first, Bybit public API fallback.
- **Fundamental/Context Agent**: CoinGecko market-cap and metadata plus DEX Screener pair/liquidity data.
- **Technical Agent**: RSI, EMA(20), EMA(50), ATR and trend from real exchange candles.
- **Signal Agent**: combines MrNasdog score, live momentum, 24h movement, volume and liquidity gates.
- **Risk Agent**: fixed account-risk sizing, stop loss and three take-profit levels.
- **Paper Execution**: stores only signals that pass the configured gates.

## Real data sources

1. MrNasdog public research pages
2. Binance public REST market data
3. Bybit public REST market data fallback
4. CoinGecko public market API
5. DEX Screener public API

Every scan result contains source names and a timestamp. If a live exchange cannot provide a symbol, that symbol is skipped rather than replaced with invented data.

## Safety

Default mode is `paper`. No exchange secret is required for discovery or market analysis. Live-money execution is intentionally gated and is not enabled by this repository's default configuration.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API:

- `GET /health`
- `GET /api/discover`
- `GET /api/scan?limit=30`
- `POST /api/paper/open/{symbol}`
- `GET /api/paper/trades`

CLI:

```bash
python -m app.cli discover
python -m app.cli scan
python -m app.cli paper
python -m app.cli trades
```

## Data integrity rule

The system must prefer **no result** over fake/stale data. MrNasdog scores are read from the live site and market prices are read from public APIs at scan time. No hardcoded price, candle, volume, market cap or token score is used.

## Disclaimer

This is research/software infrastructure, not financial advice. Paper trading does not guarantee live trading performance.
