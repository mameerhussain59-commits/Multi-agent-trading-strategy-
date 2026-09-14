# Multi-Agent Crypto Trading Strategy

A real-data multi-agent crypto research and paper-trading system. **No synthetic prices, fake candles, or fabricated market observations are used.**

## Pipeline

`MrNasdog research discovery -> live exchange market data -> CoinGecko enrichment -> DEX Screener liquidity -> technical agent -> signal agent -> portfolio/risk gates -> staged paper execution -> monitoring -> audit trail`

### Agents and controls

- **Master Agent**: orchestrates the complete scan.
- **Token Hunter**: reads MrNasdog research pages live and accepts only pages exposing an explicit 0-10 score.
- **Market Data Agent**: Binance public API first, Bybit public API fallback.
- **Fundamental/Context Agent**: CoinGecko market-cap and metadata plus DEX Screener pair/liquidity data.
- **Technical Agent**: RSI, EMA(20), EMA(50), ATR and trend from real exchange candles.
- **Signal Agent**: combines MrNasdog score, live momentum, 24h movement, volume and liquidity gates.
- **Risk Agent**: fixed account-risk sizing, stop loss and three take-profit levels.
- **Portfolio Gate**: duplicate-position protection, concurrent-position cap, total risk cap, daily-loss kill switch, total exposure cap, asset-bucket concentration control and real-candle return correlation control.
- **Paper Execution**: persists approved plans and supports staged TP1/TP2/TP3 exits with breakeven protection.
- **Position Monitor**: repeatedly reads live exchange prices and updates paper positions without inventing observations.
- **Audit Trail**: records scan decisions, provider failures and scheduler cycles in SQLite.
- **Scheduler**: continuously runs real-data scans and position monitoring with a minimum safe interval.

## Real data sources

1. MrNasdog public research pages
2. Binance public REST market data
3. Bybit public REST market data fallback
4. CoinGecko public market API
5. DEX Screener public API

Every scan result contains source names and timestamps. If a live exchange cannot provide a symbol, that symbol is skipped rather than replaced with invented data.

## Backtesting

`GET /api/backtest/{symbol}?interval=1h&limit=1000` uses real historical Binance klines only. It never generates synthetic candles. Entries use the next real candle open after a completed signal; if a real candle touches both SL and TP, the backtest assumes SL first conservatively. Open positions at the end of the dataset are marked to the final real close. The report includes return, win rate and maximum drawdown and applies the configured position-size cap.

## Safety

Default mode is `paper`. No exchange secret is required for discovery or market analysis. Live-money execution remains explicitly gated and disabled by the default configuration. The authenticated Binance adapter is intentionally not part of the automatic scan/paper pipeline; live execution should not be enabled until exchange symbol filters, protective-order handling, order idempotency and operational controls have been independently verified.

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
- `POST /api/paper/monitor`
- `GET /api/paper/trades`
- `GET /api/audit?limit=200`
- `GET /api/backtest/{symbol}?interval=1h&limit=1000`

CLI:

```bash
python -m app.cli discover
python -m app.cli scan
python -m app.cli paper
python -m app.cli monitor
python -m app.cli trades
python -m app.cli scheduler 60
python -m app.cli backtest BTC
```

The scheduler performs a live-data scan and paper-position monitoring cycle continuously. Its minimum interval is 5 seconds; a provider failure is recorded as an audit event rather than replaced with fake data.

## Data integrity rule

The system must prefer **no result** over fake/stale data. MrNasdog scores are read from the live site and market prices/candles are read from public APIs at scan time. No hardcoded price, candle, volume, market cap or token score is used.

## Disclaimer

This is research/software infrastructure, not financial advice. Paper trading does not guarantee live trading performance.
