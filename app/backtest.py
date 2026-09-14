from __future__ import annotations

from app.data import binance_klines
from app.technical import technical_analysis


def _num(value) -> float:
    return float(value)


async def backtest_binance(
    symbol: str,
    interval: str = '1h',
    limit: int = 1000,
    initial_equity: float = 10000.0,
    risk_pct: float = 0.5,
    max_position_pct: float = 10.0,
):
    """Backtest only against real Binance historical candles."""
    pair = symbol.upper().replace('/', '') + 'USDT'
    rows = await binance_klines(pair, interval, min(limit, 1000))
    if len(rows) < 100:
        raise ValueError('Not enough real historical candles')
    if initial_equity <= 0 or risk_pct <= 0 or max_position_pct <= 0:
        raise ValueError('Backtest capital and risk parameters must be positive')

    equity = float(initial_equity)
    peak_equity = equity
    max_drawdown_pct = 0.0
    trades = []
    in_trade = None

    for i in range(60, len(rows) - 1):
        closes = [_num(r[4]) for r in rows[:i]]
        highs = [_num(r[2]) for r in rows[:i]]
        lows = [_num(r[3]) for r in rows[:i]]
        tech = technical_analysis(symbol, closes, highs, lows, interval)

        if in_trade:
            candle = rows[i]
            hi = _num(candle[2])
            lo = _num(candle[3])
            exit_price = None
            reason = None
            # Conservative: if one candle touches both levels, assume SL first.
            if lo <= in_trade['sl']:
                exit_price = in_trade['sl']
                reason = 'SL'
            elif hi >= in_trade['tp']:
                exit_price = in_trade['tp']
                reason = 'TP'
            if exit_price is not None:
                pnl = (exit_price - in_trade['entry']) * in_trade['qty']
                equity += pnl
                trades.append({**in_trade, 'exit': exit_price, 'reason': reason, 'pnl': pnl, 'equity': equity})
                in_trade = None
                peak_equity = max(peak_equity, equity)
                if peak_equity > 0:
                    max_drawdown_pct = max(max_drawdown_pct, (peak_equity - equity) / peak_equity * 100.0)
            continue

        if tech.trend != 'bullish' or tech.rsi < 50:
            continue

        entry = _num(rows[i + 1][1])
        sl = max(entry - 2 * tech.atr, entry * 0.97)
        risk_per_unit = entry - sl
        if risk_per_unit <= 0:
            continue

        risk_usd = equity * (risk_pct / 100.0)
        qty_by_risk = risk_usd / risk_per_unit
        qty_by_position = (equity * (max_position_pct / 100.0)) / entry
        qty = min(qty_by_risk, qty_by_position)
        if qty <= 0:
            continue

        tp = entry + risk_per_unit * 2.0
        in_trade = {
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'qty': qty,
            'opened_at': rows[i + 1][0],
        }

    if in_trade:
        exit_price = _num(rows[-1][4])
        pnl = (exit_price - in_trade['entry']) * in_trade['qty']
        equity += pnl
        trades.append({**in_trade, 'exit': exit_price, 'reason': 'END_OF_DATA', 'pnl': pnl, 'equity': equity})
        peak_equity = max(peak_equity, equity)
        if peak_equity > 0:
            max_drawdown_pct = max(max_drawdown_pct, (peak_equity - equity) / peak_equity * 100.0)

    wins = [trade for trade in trades if trade['pnl'] > 0]
    losses = [trade for trade in trades if trade['pnl'] <= 0]
    return {
        'symbol': symbol,
        'pair': pair,
        'interval': interval,
        'candles': len(rows),
        'initial_equity': initial_equity,
        'final_equity': equity,
        'net_pnl': equity - initial_equity,
        'return_pct': (equity / initial_equity - 1) * 100,
        'trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate_pct': (len(wins) / len(trades) * 100 if trades else 0),
        'max_drawdown_pct': max_drawdown_pct,
        'data_source': 'Binance historical klines',
    }
