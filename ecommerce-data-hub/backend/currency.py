"""Quy đổi USD → VND theo tỉ giá hiện hành."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "usd_vnd_rate.json"
CACHE_TTL = timedelta(hours=6)

# Fallback khi không có mạng (cập nhật qua biến môi trường USD_VND_RATE)
DEFAULT_USD_VND = float(os.getenv("USD_VND_RATE", "25450"))


def _load_cache() -> Optional[dict]:
    if not CACHE_FILE.exists():
        return None
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(rate: float, source: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps({
            "rate": rate,
            "source": source,
            "updated_at": datetime.utcnow().isoformat(),
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def _fetch_live_rate() -> tuple[float, str]:
    """Lấy tỉ giá USD/VND từ API công khai."""
    url = "https://open.er-api.com/v6/latest/USD"
    req = urllib.request.Request(url, headers={"User-Agent": "EcommerceDataHub/1.0"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode())
    rate = float(data["rates"]["VND"])
    if rate <= 0:
        raise ValueError("Tỉ giá VND không hợp lệ")
    return rate, "open.er-api.com"


def get_usd_vnd_rate(force_refresh: bool = False) -> dict:
    """
    Trả tỉ giá USD/VND.
    Ưu tiên: biến môi trường → cache (<6h) → API live → cache cũ → mặc định.
    """
    env_rate = os.getenv("USD_VND_RATE")
    if env_rate:
        rate = float(env_rate)
        return {"rate": rate, "source": "env:USD_VND_RATE", "updated_at": None}

    if not force_refresh:
        cached = _load_cache()
        if cached:
            try:
                updated = datetime.fromisoformat(cached["updated_at"])
                if datetime.utcnow() - updated < CACHE_TTL:
                    return {
                        "rate": float(cached["rate"]),
                        "source": cached.get("source", "cache"),
                        "updated_at": cached.get("updated_at"),
                    }
            except (ValueError, TypeError, KeyError):
                pass

    try:
        rate, source = _fetch_live_rate()
        _save_cache(rate, source)
        return {"rate": rate, "source": source, "updated_at": datetime.utcnow().isoformat()}
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError, TimeoutError):
        cached = _load_cache()
        if cached and cached.get("rate"):
            return {
                "rate": float(cached["rate"]),
                "source": f"cache (offline): {cached.get('source', '?')}",
                "updated_at": cached.get("updated_at"),
            }
        return {"rate": DEFAULT_USD_VND, "source": "default (offline)", "updated_at": None}


def is_usd_currency(currency: Optional[str]) -> bool:
    if not currency:
        return False
    c = str(currency).strip().upper()
    return c in ("USD", "US$", "$", "US DOLLAR", "ĐÔ LA MỸ")


# Các cột tiền trong Creative data cần quy đổi
AD_CREATIVE_MONEY_FIELDS = ("cost", "cost_per_order", "gross_revenue")


def convert_ad_row_usd_to_vnd(row: dict, rate: float) -> dict:
    """Quy đổi các trường tiền USD → VND, lưu tỉ giá đã dùng."""
    out = dict(row)
    for field in AD_CREATIVE_MONEY_FIELDS:
        val = out.get(field)
        if val is not None:
            out[field] = round(float(val) * rate, 0)
    out["currency"] = "VND"
    out["_fx_rate"] = rate
    out["_fx_from"] = "USD"
    return out
