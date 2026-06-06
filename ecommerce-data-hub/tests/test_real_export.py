"""Kiểm thử parser với schema export TikTok thực tế (2026)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from parsers import (
    parse_date_flexible,
    parse_datetime_tiktok,
    parse_tiktok_ad_creative,
    parse_tiktok_affiliate_creator,
    parse_tiktok_affiliate_video,
    parse_vn_number,
)

REAL = ROOT / "tests" / "samples" / "real"


def _to_xlsx(df: pd.DataFrame, path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False, engine="openpyxl")
    return path.read_bytes()


def build_real_fixtures():
    creative = pd.DataFrame([
        {
            "ID video": "7640570208339512584",
            "Tiêu đề video": "Bột ngũ cốc thực dưỡng...",
            "Tài khoản TikTok": "Bí Kíp Khoẻ Re",
            "Loại nội dung sáng tạo": "Video",
            "Nguồn video": "",
            "Trạng thái": "Bị loại trừ",
            "Thời gian đăng": "2026-05-17 05:30",
            "Chi phí": 8913183,
            "Số lượng đơn hàng SKU": 180,
            "Chi phí cho mỗi đơn hàng": 49518,
            "Doanh thu gộp": 31061735,
            "ROI": 3.48,
            "Số lượt hiển thị quảng cáo sản phẩm": 126094,
            "Số lượt nhấp vào quảng cáo sản phẩm": 3155,
            "Tỷ lệ nhấp vào quảng cáo sản phẩm": "2.50%",
            "Tỷ lệ chuyển đổi quảng cáo": "5.07%",
            "Tỷ lệ xem video quảng cáo trong 2 giây": "43.45%",
            "Tỷ lệ xem video quảng cáo trong 6 giây": "17.11%",
            "Tỷ lệ xem 25% thời lượng video quảng cáo": "9.43%",
            "Tỷ lệ xem 50% thời lượng video quảng cáo": "5.63%",
            "Tỷ lệ xem 75% thời lượng video quảng cáo": "3.51%",
            "Tỷ lệ xem 100% thời lượng video quảng cáo": "2.35%",
            "Đơn vị tiền tệ": "VND",
        },
        {
            "ID video": "N/A",
            "Tiêu đề video": "-",
            "Tài khoản TikTok": "-",
            "Loại nội dung sáng tạo": "Thẻ sản phẩm",
            "Trạng thái": "Đang phân phối",
            "Thời gian đăng": "-",
            "Chi phí": 6942184,
            "Số lượng đơn hàng SKU": 707,
            "Doanh thu gộp": 132183523,
            "ROI": 19.04,
            "Số lượt hiển thị quảng cáo sản phẩm": 124003,
            "Tỷ lệ nhấp vào quảng cáo sản phẩm": "3.91%",
            "Tỷ lệ chuyển đổi quảng cáo": "2.66%",
            "Tỷ lệ xem video quảng cáo trong 2 giây": "-",
            "Đơn vị tiền tệ": "VND",
        },
    ])

    creators = pd.DataFrame([
        {
            "Tên người dùng của nhà sáng tạo": "songkhoemoingay._",
            "GMV liên kết": 2111928081,
            "GMV LIVE của liên kết": 0,
            "GMV video link bán hàng của liên kết": 2107788911,
            "GMV thẻ sản phẩm của liên kết": 4139170,
            "Sản phẩm liên kết đã bán": 17,
            "Số món bán ra": 4396,
            "Hoa hồng ước tính": 23761095,
            "Phí cố định ước tính": "--",
            "Giá trị đơn hàng trung bình": 504160,
            "Đơn hàng liên kết": 4189,
            "Tỷ lệ nhấp (CTR)": "2%",
            "GMV cộng tác mục tiêu": 2051196206,
            "Hoa hồng ước tính trong cộng tác mục tiêu": 3948742,
            "GMV cộng tác mở": 59638859,
            "Hoa hồng ước tính của cộng tác mở": 1865539,
            "GMV đã hoàn tiền từ liên kết": 544692391,
            "Người theo dõi của liên kết": 20019,
        },
        {
            "Tên người dùng của nhà sáng tạo": "liengia89",
            "GMV liên kết": 397891877,
            "GMV LIVE của liên kết": 280713983,
            "GMV video link bán hàng của liên kết": 96589013,
            "Đơn hàng liên kết": 474,
            "Tỷ lệ nhấp (CTR)": "5%",
            "GMV cộng tác mục tiêu": 397891877,
            "GMV cộng tác mở": 0,
        },
    ])

    videos = pd.DataFrame([
        {
            "Tên video": "Tặng ngay cái muỗng vàng...",
            "Ngày đăng video": "2026-04-03",
            "Tên người dùng của nhà sáng tạo": "thuanh.review",
            "Bình luận của video link bán hàng": 2,
            "Lượt thích của video link bán hàng": 16,
            "Đơn hàng liên kết": 84,
            "Số món bán ra qua liên kết ": 85,
            "Giá trị đơn hàng trung bình của video link bán hàng": 277311,
            "GMV": 17050042,
            "GMV video link bán hàng của liên kết": 23294143,
            "Hoa hồng ước tính": 3462327,
            "Phí cố định ước tính": "--",
            "CTR của liên kết": "6%",
            "GPM của video link bán hàng": 1229307,
        },
    ])

    return (
        _to_xlsx(creative, REAL / "Creative_data_real.xlsx"),
        _to_xlsx(creators, REAL / "Creator_List_real.xlsx"),
        _to_xlsx(videos, REAL / "Creator_Video_List_real.xlsx"),
    )


def test_real_creative():
    content = build_real_fixtures()[0]
    rows = parse_tiktok_ad_creative(content)
    assert len(rows) == 2, f"Expected 2 rows (video + thẻ SP), got {len(rows)}"

    video = rows[0]
    assert video["video_id"] == "7640570208339512584"
    assert video["posted_at"].strftime("%Y-%m-%d %H:%M") == "2026-05-17 05:30"
    assert video["cost"] == 8913183.0
    assert video["product_ad_ctr"] == 2.50
    assert video["view_rate_2s"] == 43.45

    card = rows[1]
    assert card["video_id"] is None
    assert card["creative_type"] == "Thẻ sản phẩm"
    assert card["cost"] == 6942184.0
    assert card["gross_revenue"] == 132183523.0
    assert card["view_rate_2s"] is None
    print("✓ Real creative data OK")


def test_real_creator():
    content = build_real_fixtures()[1]
    rows = parse_tiktok_affiliate_creator(content)
    assert len(rows) == 2

    s = rows[0]
    assert s["creator_username"] == "songkhoemoingay._"
    assert s["gmv"] == 2111928081.0
    assert s["estimated_flat_fee"] is None  # --
    assert s["ctr"] == 2.0
    assert s["gmv_collab_target"] == 2051196206.0
    assert s["gmv_collab_open"] == 59638859.0
    assert s["gmv_collab"] == 2051196206.0 + 59638859.0

    l = rows[1]
    assert l["gmv_live"] == 280713983.0
    assert l["gmv_collab"] == 397891877.0
    print("✓ Real creator list OK")


def test_real_video():
    content = build_real_fixtures()[2]
    rows = parse_tiktok_affiliate_video(content)
    assert len(rows) == 1
    v = rows[0]
    assert str(v["posted_date"]) == "2026-04-03"
    assert v["gmv"] == 17050042.0
    assert v["estimated_flat_fee"] is None
    assert v["linked_ctr"] == 6.0
    print("✓ Real creator video OK")


def test_helpers():
    assert parse_datetime_tiktok("2026-05-17 05:30").year == 2026
    assert str(parse_date_flexible("2026-04-03")) == "2026-04-03"
    assert parse_vn_number("--") is None
    print("✓ Helpers OK")


if __name__ == "__main__":
    test_helpers()
    test_real_creative()
    test_real_creator()
    test_real_video()
    print("\n✓ All real export tests passed")
