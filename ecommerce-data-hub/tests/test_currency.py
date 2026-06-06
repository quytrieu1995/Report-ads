"""Test quy đổi USD → VND khi ingest Creative data."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from parsers import parse_tiktok_ad_creative

SAMPLES = ROOT / "tests" / "samples" / "real"


def test_usd_to_vnd_conversion():
    df = pd.DataFrame([
        {
            "ID video": "7621554711556132116",
            "Tiêu đề video": "Không tin luôn anh chị em...",
            "Tài khoản TikTok": "🌻 Xuyến Miền Tây(N.Phụ)☘️",
            "Loại nội dung sáng tạo": "Video",
            "Trạng thái": "Đang phân phối",
            "Thời gian đăng": "2026-03-26 20:24",
            "Chi phí": 754.83,
            "Số lượng đơn hàng SKU": 115,
            "Chi phí cho mỗi đơn hàng": 6.56,
            "Doanh thu gộp": 653.09,
            "ROI": 0.87,
            "Số lượt hiển thị quảng cáo sản phẩm": 1413460,
            "Số lượt nhấp vào quảng cáo sản phẩm": 91808,
            "Tỷ lệ nhấp vào quảng cáo sản phẩm": "6.50%",
            "Tỷ lệ chuyển đổi quảng cáo": "0.41%",
            "Đơn vị tiền tệ": "USD",
        },
        {
            "ID video": "N/A",
            "Tiêu đề video": "-",
            "Loại nội dung sáng tạo": "Thẻ sản phẩm",
            "Chi phí": 451.91,
            "Doanh thu gộp": 13468.95,
            "Đơn vị tiền tệ": "USD",
        },
    ])
    path = SAMPLES / "Creative_usd_convert_test.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False, engine="openpyxl")
    content = path.read_bytes()

    mock_rate = 25500.0
    with patch("currency.get_usd_vnd_rate", return_value={"rate": mock_rate, "source": "test"}):
        rows = parse_tiktok_ad_creative(content)

    assert len(rows) == 2
    v = rows[0]
    assert v["currency"] == "VND"
    assert v["cost"] == round(754.83 * mock_rate)
    assert v["gross_revenue"] == round(653.09 * mock_rate)
    assert v["cost_per_order"] == round(6.56 * mock_rate)
    assert v["roi"] == 0.87  # ROI giữ nguyên (tỉ lệ)
    assert v["_fx_rate"] == mock_rate

    card = rows[1]
    assert card["currency"] == "VND"
    assert card["cost"] == round(451.91 * mock_rate)
    print("✓ USD→VND conversion OK")


if __name__ == "__main__":
    test_usd_to_vnd_conversion()
