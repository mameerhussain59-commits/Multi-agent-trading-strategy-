# Multi-Agent Crypto Trading Strategy

A real-data, multi-agent crypto research and paper-trading system. The project discovers tokens from MrNasdog, enriches them with live market data from free/public APIs, runs deterministic research agents, produces trade plans with entry/stop-loss/take-profit levels, and records paper trades.

## Data sources

- MrNasdog: scored-token discovery / research metadata
- DEX Screener: token/pair discovery and DEX market data
- CoinGecko: market-cap, price and market metadata when available
- Binance public API: live spot klines/order-book/ticker data
- Bybit public API: live market data fallback

No fake/synthetic market prices are generated. Every market observation carries a source and timestamp.

## Safety defaults

- `TRADING_MODE=paper`
- Live exchange execution is not enabled by default.
- Risk sizing is deterministic and capped.
- The system rejects stale market data.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs`.

### CLI

```bash
python -m app.cli discover
python -m app.cli scan
python -m app.cli paper
```

## Architecture

`Discovery -> Market Data -> Fundamentals -> Technical -> Signal -> Risk -> Paper Execution -> Monitoring`

The orchestration layer is in `app/orchestrator.py`. Agents exchange typed Pydantic models rather than unstructured text.

## Environment

Copy `.env.example` to `.env`. API keys are optional for the free/public data paths. `COINGECKO_API_KEY` can be supplied when the selected CoinGecko endpoint requires it.

## Disclaimer

This is research and software infrastructure, not financial advice. The project is intentionally paper-trading-first.
