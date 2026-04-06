from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import CoinMarketSnapshot


DATA_PATH = Path(__file__).with_name("sample_market_data.json")


def load_market_data() -> List[CoinMarketSnapshot]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [CoinMarketSnapshot(**item) for item in raw]
