from __future__ import annotations

from app.audit import record_event
from app.config import settings
from app.data import coingecko_coin, dexscreener_token, live_market, mrnasdog_scored_tokens
from app.models import MarketSnapshot, ScanResult, Token
from app.portfolio import portfolio_gate
from app.risk import make_trade_plan, score_signal
from app.technical import technical_analysis


class TokenHunterAgent:
    async def run(self, limit=30):
        rows = await mrnasdog_scored_tokens()
        return [
            Token(symbol=x['symbol'], source='mrnasdog', source_score=x['score'], source_url=x['url'])
            for x in rows[:limit]
        ]


class MarketDataAgent:
    async def run(self, token):
        live = await live_market(token.symbol)
        cg = await coingecko_coin(token.symbol)
        dex = await dexscreener_token(token.symbol)
        liquidity = float((dex or {}).get('liquidity', {}).get('usd') or 0)
        spread = None
        ob = live.get('order_book') or {}
        if ob.get('bids') and ob.get('asks'):
            bid, ask = float(ob['bids'][0][0]), float(ob['asks'][0][0])
            mid = (ask + bid) / 2
            if mid > 0:
                spread = ((ask - bid) / mid) * 100
        return live, cg, dex, liquidity, spread


class TechnicalAgent:
    def run(self, token, live):
        rows = live['candles']
        closes = [float(r[4]) for r in rows]
        highs = [float(r[2]) for r in rows]
        lows = [float(r[3]) for r in rows]
        return technical_analysis(token.symbol, closes, highs, lows)


class SignalAgent:
    def run(self, token, market, technical, liquidity_ok=True):
        return score_signal(
            token.source_score,
            market.change_24h,
            technical.momentum_score,
            market.volume_24h > 0,
            liquidity_ok,
        )


class RiskAgent:
    def run(self, token, market, technical, score, liquidity_ok, spread_ok):
        warnings = []
        if settings.require_dex_liquidity and not liquidity_ok:
            warnings.append('DEX liquidity below configured minimum or unavailable')
        if not spread_ok:
            warnings.append('Exchange spread above configured maximum')
        return make_trade_plan(
            token.symbol,
            market.price,
            technical.atr,
            score,
            [
                f'MrNasdog score={token.source_score}/10',
                f'{market.exchange} live price',
                f'{technical.timeframe} trend={technical.trend}',
            ],
            warnings,
        )


class MasterAgent:
    def __init__(self):
        self.hunter = TokenHunterAgent()
        self.market = MarketDataAgent()
        self.tech = TechnicalAgent()
        self.signal = SignalAgent()
        self.risk = RiskAgent()

    async def scan(self, limit=30):
        results = []
        for token in await self.hunter.run(limit):
            try:
                live, cg, dex, liquidity, spread = await self.market.run(token)
                liquidity_ok = liquidity >= settings.min_liquidity_usd
                spread_ok = spread is None or spread <= settings.max_spread_pct
                market = MarketSnapshot(
                    symbol=token.symbol,
                    pair=live['pair'],
                    price=live['price'],
                    change_24h=live['change_24h'],
                    volume_24h=live['volume_24h'],
                    high_24h=live['high_24h'],
                    low_24h=live['low_24h'],
                    market_cap=(cg or {}).get('market_cap'),
                    liquidity_usd=liquidity,
                    spread_pct=spread,
                    exchange=live['exchange'],
                    source='live_exchange+coingecko+dexscreener',
                )
                technical = self.tech.run(token, live)
                score = self.signal.run(token, market, technical, liquidity_ok)
                plan = self.risk.run(token, market, technical, score, liquidity_ok, spread_ok)
                allowed, portfolio_warnings = portfolio_gate(plan)
                if portfolio_warnings:
                    plan.warnings.extend(portfolio_warnings)
                plan.executable = plan.executable and allowed
                result = ScanResult(
                    token=token,
                    market=market,
                    technical=technical,
                    trade=plan,
                    data_sources=['MrNasdog', 'Binance/Bybit', 'CoinGecko', 'DEX Screener'],
                )
                results.append(result)
                record_event('scan_result', token.symbol, {
                    'score': plan.score,
                    'executable': plan.executable,
                    'exchange': market.exchange,
                    'price': market.price,
                    'observed_at': getattr(live, 'timestamp', None) if not isinstance(live, dict) else live.get('timestamp'),
                    'warnings': plan.warnings,
                    'sources': result.data_sources,
                })
            except Exception as exc:
                record_event('scan_error', token.symbol, {'error': str(exc)})
                continue
        return sorted(results, key=lambda x: x.trade.score, reverse=True)
