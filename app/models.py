from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    conservative = "conservative"
    balanced = "balanced"
    aggressive = "aggressive"


class UserProfile(BaseModel):
    capital_eur: float = Field(gt=0, description="Verfügbares Kapital in EUR")
    risk_level: RiskLevel
    horizon_months: int = Field(ge=1, le=120)
    max_positions: int = Field(default=5, ge=1, le=20)
    max_drawdown_tolerance_pct: float = Field(default=20, ge=1, le=95)


class CoinMarketSnapshot(BaseModel):
    symbol: str
    name: str
    price: float
    market_cap_rank: int
    volume_24h_usd: float
    price_change_7d_pct: float
    price_change_30d_pct: float
    rsi_14: float
    sma_50_above_sma_200: bool
    funding_bias: float = Field(description="-1 bearish, 0 neutral, 1 bullish")
    sentiment_score: float = Field(description="0-100")
    ecosystem_strength: float = Field(description="0-100")
    volatility_score: float = Field(description="0-100, higher = riskier")
    liquidity_score: float = Field(description="0-100")


class CoinScore(BaseModel):
    symbol: str
    name: str
    total_score: float
    risk_score: float
    momentum_score: float
    quality_score: float
    reasons: List[str]


class PositionPlan(BaseModel):
    symbol: str
    name: str
    allocation_pct: float
    allocation_eur: float
    entry_style: str
    take_profit_rule: str
    risk_rule: str
    rationale: List[str]


class InvestmentPlan(BaseModel):
    profile: UserProfile
    market_regime: str
    summary: str
    positions: List[PositionPlan]
    cash_buffer_pct: float
    portfolio_rules: List[str]
    rejected_symbols: List[str]
    notes: List[str]


class PlanRequest(BaseModel):
    profile: UserProfile
    symbols: Optional[List[str]] = None
