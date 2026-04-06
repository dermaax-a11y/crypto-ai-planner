from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .config import get_settings
from .data_loader import load_market_data
from .models import PlanRequest, RiskLevel, UserProfile
from .scoring import build_dashboard, build_plan, score_coin

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class WhatIfRequest(BaseModel):
    symbol: str
    price_change_30d_pct: float
    sentiment_score: float
    liquidity_score: float
    volatility_score: float
    risk_level: RiskLevel


def _context_from_profile(profile: UserProfile):
    market_data = load_market_data()
    plan = build_plan(PlanRequest(profile=profile), market_data)
    scores = [score_coin(c, profile.risk_level) for c in market_data]
    scores = sorted(scores, key=lambda x: x.total_score, reverse=True)
    dashboard = build_dashboard(plan, scores, market_data)
    return {
        "plan": plan,
        "scores": scores,
        "risk_levels": list(RiskLevel),
        "dashboard": dashboard,
        "market_data": market_data,
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    default_profile = UserProfile(
        capital_eur=1500,
        risk_level=RiskLevel.balanced,
        horizon_months=24,
        max_positions=5,
        max_drawdown_tolerance_pct=18,
    )
    return templates.TemplateResponse(request, "index.html", _context_from_profile(default_profile))


@app.post("/", response_class=HTMLResponse)
def generate_from_form(
    request: Request,
    capital_eur: float = Form(...),
    risk_level: str = Form(...),
    horizon_months: int = Form(...),
    max_positions: int = Form(...),
    max_drawdown_tolerance_pct: float = Form(...),
):
    profile = UserProfile(
        capital_eur=capital_eur,
        risk_level=RiskLevel(risk_level),
        horizon_months=horizon_months,
        max_positions=max_positions,
        max_drawdown_tolerance_pct=max_drawdown_tolerance_pct,
    )
    return templates.TemplateResponse(request, "index.html", _context_from_profile(profile))


@app.get("/health")
def health():
    return {"status": "ok", "app": app.title, "version": app.version}


@app.get("/api/market")
def get_market_data():
    return load_market_data()


@app.post("/api/plan")
def create_plan(request_body: PlanRequest):
    return build_plan(request_body, load_market_data())


@app.post("/api/what-if")
def what_if(request_body: WhatIfRequest):
    market_data = load_market_data()
    coin = next((c for c in market_data if c.symbol.lower() == request_body.symbol.lower()), None)
    if not coin:
        return JSONResponse(status_code=404, content={"error": "Symbol nicht gefunden"})

    coin.price_change_30d_pct = request_body.price_change_30d_pct
    coin.sentiment_score = request_body.sentiment_score
    coin.liquidity_score = request_body.liquidity_score
    coin.volatility_score = request_body.volatility_score
    score = score_coin(coin, request_body.risk_level)
    return {"score": score, "coin": coin}
