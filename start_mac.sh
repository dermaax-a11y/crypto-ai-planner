#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

export $(grep -v '^#' .env.example | xargs)
uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
