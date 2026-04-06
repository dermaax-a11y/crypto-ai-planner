from __future__ import annotations

from statistics import mean
from typing import Iterable, List

from .models import CoinMarketSnapshot, CoinScore, InvestmentPlan, PlanRequest, PositionPlan, RiskLevel


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


RISK_PROFILES = {
    RiskLevel.conservative: {
        "max_volatility": 55,
        "min_liquidity": 65,
        "momentum_weight": 0.20,
        "quality_weight": 0.55,
        "risk_weight": 0.25,
        "cash_buffer_pct": 30,
        "max_single_position": 18,
    },
    RiskLevel.balanced: {
        "max_volatility": 72,
        "min_liquidity": 50,
        "momentum_weight": 0.30,
        "quality_weight": 0.45,
        "risk_weight": 0.25,
        "cash_buffer_pct": 15,
        "max_single_position": 28,
    },
    RiskLevel.aggressive: {
        "max_volatility": 90,
        "min_liquidity": 35,
        "momentum_weight": 0.42,
        "quality_weight": 0.35,
        "risk_weight": 0.23,
        "cash_buffer_pct": 5,
        "max_single_position": 40,
    },
}


def score_coin(coin: CoinMarketSnapshot, risk_level: RiskLevel) -> CoinScore:
    profile = RISK_PROFILES[risk_level]

    momentum = 0.0
    momentum += 15 if coin.sma_50_above_sma_200 else 0
    momentum += clamp(coin.price_change_7d_pct + 10, 0, 20)
    momentum += clamp((coin.price_change_30d_pct / 2) + 15, 0, 25)
    momentum += clamp((coin.rsi_14 - 35) * 1.5, 0, 20)
    momentum += 10 if coin.funding_bias > 0 else 4 if coin.funding_bias == 0 else 0
    momentum = clamp(momentum, 0, 100)

    quality = 0.0
    quality += clamp(100 - coin.market_cap_rank, 0, 20)
    quality += clamp(coin.liquidity_score * 0.25, 0, 25)
    quality += clamp(coin.sentiment_score * 0.20, 0, 20)
    quality += clamp(coin.ecosystem_strength * 0.35, 0, 35)
    quality = clamp(quality, 0, 100)

    risk_score = 0.0
    risk_score += clamp(100 - coin.volatility_score, 0, 40)
    risk_score += clamp(coin.liquidity_score * 0.35, 0, 35)
    risk_score += 15 if coin.market_cap_rank <= 20 else 8 if coin.market_cap_rank <= 50 else 2
    risk_score += 10 if 45 <= coin.rsi_14 <= 68 else 4
    risk_score = clamp(risk_score, 0, 100)

    total = (
        momentum * profile["momentum_weight"]
        + quality * profile["quality_weight"]
        + risk_score * profile["risk_weight"]
    )

    reasons: List[str] = []
    if coin.sma_50_above_sma_200:
        reasons.append("50-Tage-Schnitt liegt über dem 200-Tage-Schnitt")
    if coin.liquidity_score >= 70:
        reasons.append("hohe Liquidität")
    if coin.ecosystem_strength >= 75:
        reasons.append("starkes Ökosystem")
    if coin.volatility_score > profile["max_volatility"]:
        reasons.append("erhöhte Volatilität")
    if coin.rsi_14 > 72:
        reasons.append("möglicherweise kurzfristig überhitzt")
    if coin.price_change_30d_pct < -10:
        reasons.append("schwache 30-Tage-Entwicklung")

    return CoinScore(
        symbol=coin.symbol,
        name=coin.name,
        total_score=round(total, 2),
        risk_score=round(risk_score, 2),
        momentum_score=round(momentum, 2),
        quality_score=round(quality, 2),
        reasons=reasons or ["gemischtes Signalbild"],
    )


def detect_market_regime(coins: Iterable[CoinMarketSnapshot]) -> str:
    coins = list(coins)
    bullish = sum(1 for c in coins if c.sma_50_above_sma_200 and c.price_change_30d_pct > 0)
    ratio = bullish / max(len(coins), 1)
    if ratio >= 0.7:
        return "bullish"
    if ratio >= 0.4:
        return "neutral"
    return "defensive"


def build_plan(request: PlanRequest, market_data: List[CoinMarketSnapshot]) -> InvestmentPlan:
    profile_cfg = RISK_PROFILES[request.profile.risk_level]
    filtered = [c for c in market_data if not request.symbols or c.symbol in request.symbols]

    eligible: List[CoinMarketSnapshot] = []
    rejected: List[str] = []
    for coin in filtered:
        if coin.liquidity_score < profile_cfg["min_liquidity"]:
            rejected.append(coin.symbol)
            continue
        if coin.volatility_score > profile_cfg["max_volatility"] and request.profile.risk_level != RiskLevel.aggressive:
            rejected.append(coin.symbol)
            continue
        eligible.append(coin)

    scores = sorted(
        [score_coin(coin, request.profile.risk_level) for coin in eligible],
        key=lambda x: x.total_score,
        reverse=True,
    )
    selected = scores[: request.profile.max_positions]
    regime = detect_market_regime(filtered or market_data)

    investable_pct = 100 - profile_cfg["cash_buffer_pct"]
    base_weights = [s.total_score for s in selected]
    total_weights = sum(base_weights) or 1

    raw_allocations = [(s.total_score / total_weights) * investable_pct for s in selected]
    capped_allocations = [min(a, profile_cfg["max_single_position"]) for a in raw_allocations]
    remainder = investable_pct - sum(capped_allocations)

    if remainder > 0 and capped_allocations:
        eligible_idx = [i for i, a in enumerate(capped_allocations) if a < profile_cfg["max_single_position"]]
        if eligible_idx:
            bonus = remainder / len(eligible_idx)
            for i in eligible_idx:
                capped_allocations[i] += bonus

    positions: List[PositionPlan] = []
    for s, allocation_pct in zip(selected, capped_allocations):
        allocation_pct = round(allocation_pct, 2)
        allocation_eur = round(request.profile.capital_eur * allocation_pct / 100, 2)
        entry_style = (
            "gestaffelt in 3 Tranchen über 10-20 Tage"
            if regime != "bullish" or request.profile.risk_level == RiskLevel.conservative
            else "50% sofort, 50% bei Rücksetzer oder Bestätigung"
        )
        take_profit = (
            "Teilgewinnmitnahmen bei +25%, +50% und Trailing-Stop für Restposition"
            if request.profile.risk_level != RiskLevel.aggressive
            else "Teilgewinnmitnahmen bei +30%, +60%, +100%"
        )
        risk_rule = (
            f"maximal {round(min(request.profile.max_drawdown_tolerance_pct / 2, 15), 1)}% Positionsverlust tolerieren; bei Trendbruch neu bewerten"
        )
        positions.append(
            PositionPlan(
                symbol=s.symbol,
                name=s.name,
                allocation_pct=allocation_pct,
                allocation_eur=allocation_eur,
                entry_style=entry_style,
                take_profit_rule=take_profit,
                risk_rule=risk_rule,
                rationale=s.reasons,
            )
        )

    summary = {
        "bullish": "Marktumfeld konstruktiv. Fokus auf qualitativ starke Trends, trotzdem gestaffelte Einstiege.",
        "neutral": "Gemischtes Umfeld. Breite Streuung und disziplinierte Einstiege sind wichtiger als aggressives Nachjagen.",
        "defensive": "Vorsichtiges Umfeld. Hoher Cash-Anteil und strengere Risikoregeln haben Priorität.",
    }[regime]

    rules = [
        "Nie alles auf einmal investieren; Käufe staffeln.",
        "Keine Position vergrößern, nur weil sie stark gefallen ist, ohne neue Bestätigung.",
        "Jede Woche Marktregime, Dominanz, Liquidität und Trend prüfen.",
        "Einzeltitelrisiko begrenzen; keine FOMO-Käufe nach parabolischen Anstiegen.",
        "Nur Kapital einsetzen, dessen Verlust finanziell verkraftbar wäre.",
    ]

    notes = [
        "Die App arbeitet aktuell mit Beispieldaten und einer transparenten Regel-Engine.",
        "Für ein Live-Produkt sollten Preis-, On-Chain- und Sentiment-Daten automatisiert eingespeist werden.",
        "Kein Modell kann hohe Renditen sicher garantieren; die App soll Disziplin und Entscheidungsqualität erhöhen.",
    ]

    return InvestmentPlan(
        profile=request.profile,
        market_regime=regime,
        summary=summary,
        positions=positions,
        cash_buffer_pct=profile_cfg["cash_buffer_pct"],
        portfolio_rules=rules,
        rejected_symbols=rejected,
        notes=notes,
    )


def build_dashboard(plan: InvestmentPlan, scores: List[CoinScore], market_data: List[CoinMarketSnapshot]) -> dict:
    avg_score = round(mean([s.total_score for s in scores]), 1) if scores else 0
    best_coin = scores[0].symbol if scores else "-"
    investable_eur = round(plan.profile.capital_eur * (100 - plan.cash_buffer_pct) / 100, 2)
    avg_30d = round(mean([c.price_change_30d_pct for c in market_data]), 1) if market_data else 0
    heat = "niedrig" if avg_30d < 5 else "mittel" if avg_30d < 15 else "hoch"
    return {
        "avg_score": avg_score,
        "best_coin": best_coin,
        "investable_eur": investable_eur,
        "market_heat": heat,
        "avg_30d": avg_30d,
    }
