# Crypto AI Planner

Seriöse, lokal lauffähige Krypto-Web-App mit FastAPI. Sie erstellt aus Risikoprofil, Kapital und Marktparametern einen nachvollziehbaren Investmentplan statt Renditen zu versprechen.

## Was die App kann
- Web-Oberfläche mit Formular und Investmentplan
- REST API für `/api/plan`, `/api/market`, `/api/what-if`
- transparente Scoring-Engine statt Blackbox
- Marktregime-Bewertung
- Dockerfile, `docker-compose.yml`, `render.yaml`
- einfacher Mac-Start per `start_mac.sh`
- Tests

## Projektstruktur
```text
crypto_ai_planner/
├── app/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── .env.example
├── start_mac.sh
└── README.md
```

## Lokaler Start auf dem Mac

### Variante A – schnell per Terminal
```bash
cd crypto_ai_planner
chmod +x start_mac.sh
./start_mac.sh
```

Danach im Browser:
```text
http://127.0.0.1:8000/
```

### Variante B – manuell
```bash
cd crypto_ai_planner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
```

## Docker
```bash
docker compose up --build
```

## API-Beispiele

### Plan berechnen
```bash
curl -X POST http://127.0.0.1:8000/api/plan \
  -H "Content-Type: application/json" \
  -d '{
    "profile": {
      "capital_eur": 1500,
      "risk_level": "balanced",
      "horizon_months": 24,
      "max_positions": 5,
      "max_drawdown_tolerance_pct": 18
    }
  }'
```

### What-if Analyse
```bash
curl -X POST http://127.0.0.1:8000/api/what-if \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SOL",
    "price_change_30d_pct": 18,
    "sentiment_score": 76,
    "liquidity_score": 90,
    "volatility_score": 68,
    "risk_level": "balanced"
  }'
```

## Upload / Deployment
Die App kann direkt mit Docker auf Plattformen wie Render deployed werden.

### Render mit Docker
1. Projekt zu GitHub hochladen.
2. Bei Render einen neuen **Web Service** anlegen.
3. GitHub-Repo auswählen.
4. Render erkennt das `Dockerfile` oder `render.yaml`.
5. Deploy starten.
6. Nach dem Build die öffentliche URL öffnen.

## Wichtiger Hinweis
Die App ist funktionsfähig und seriös strukturiert, arbeitet in dieser Version aber mit Beispieldaten. Für eine echte Live-App müssten Börsen-, News-, On-Chain- und Sentimentdaten angebunden sowie Nutzerkonten, Datenbank, Hosting, Monitoring und Alerts ergänzt werden.
