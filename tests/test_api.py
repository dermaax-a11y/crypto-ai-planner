from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Crypto AI Planner" in response.text


def test_api_plan_returns_positions():
    payload = {
        "profile": {
            "capital_eur": 1500,
            "risk_level": "balanced",
            "horizon_months": 24,
            "max_positions": 5,
            "max_drawdown_tolerance_pct": 18,
        }
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "positions" in body
    assert len(body["positions"]) > 0


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_what_if_endpoint():
    payload = {
        "symbol": "SOL",
        "price_change_30d_pct": 18,
        "sentiment_score": 76,
        "liquidity_score": 90,
        "volatility_score": 68,
        "risk_level": "balanced",
    }
    response = client.post("/api/what-if", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["score"]["symbol"] == "SOL"
