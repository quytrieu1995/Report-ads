"""Kiểm thử parser với schema export TikTok thực tế (2026)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from parsers import (
    detect_source_type,
    parse_date_flexible,
    parse_datetime_tiktok,
    parse_tiktok_ad_creative,
    parse_tiktok_affiliate_creator,
    parse_tiktok_affiliate_product,
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


def test_real_creative_usd_schema():
    """Schema ID video + USD — tự quy đổi sang VND."""
    from unittest.mock import patch

    creative = pd.DataFrame([
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
            "Tỷ lệ xem video quảng cáo trong 2 giây": "21.71%",
            "Tỷ lệ xem video quảng cáo trong 6 giây": "6.77%",
            "Tỷ lệ xem 25% thời lượng video quảng cáo": "2.65%",
            "Tỷ lệ xem 50% thời lượng video quảng cáo": "0.78%",
            "Tỷ lệ xem 75% thời lượng video quảng cáo": "0.41%",
            "Tỷ lệ xem 100% thời lượng video quảng cáo": "0.16%",
            "Đơn vị tiền tệ": "USD",
        },
        {
            "ID video": "N/A",
            "Tiêu đề video": "-",
            "Tài khoản TikTok": "-",
            "Loại nội dung sáng tạo": "Thẻ sản phẩm",
            "Trạng thái": "Đang phân phối",
            "Thời gian đăng": "-",
            "Chi phí": 451.91,
            "Số lượng đơn hàng SKU": 1954,
            "Doanh thu gộp": 13468.95,
            "ROI": 29.80,
            "Số lượt hiển thị quảng cáo sản phẩm": 126826,
            "Tỷ lệ nhấp vào quảng cáo sản phẩm": "6.12%",
            "Tỷ lệ chuyển đổi quảng cáo": "2.54%",
            "Tỷ lệ xem video quảng cáo trong 2 giây": "-",
            "Đơn vị tiền tệ": "USD",
        },
    ])
    content = _to_xlsx(creative, REAL / "Creative_data_usd_new_schema.xlsx")
    assert detect_source_type("Creative_data.xlsx", content) == "tiktok_ad_creative"
    with patch("currency.get_usd_vnd_rate", return_value={"rate": 25500.0, "source": "test"}):
        rows = parse_tiktok_ad_creative(content)
    assert len(rows) == 2

    v = rows[0]
    assert v["video_id"] == "7621554711556132116"
    assert v["video_title"].startswith("Không tin")
    assert v["currency"] == "VND"
    assert v["cost"] == round(754.83 * 25500)
    assert v["gross_revenue"] == round(653.09 * 25500)
    assert v["product_ad_ctr"] == 6.50

    card = rows[1]
    assert card["video_id"] is None
    assert card["creative_type"] == "Thẻ sản phẩm"
    assert card["currency"] == "VND"
    assert card["cost"] == round(451.91 * 25500)
    print("✓ Real creative USD → VND OK")


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


def test_real_video_english_schema():
    """Creator Video List — cột tiếng Anh (export 2026)."""
    videos = pd.DataFrame([
        {
            "Video name": "Săn ngay combo 6 LON NGHỆ GẠO LỨT...",
            "Video post date": "2026-03-28",
            "Creator username": "songkhoemoingay._",
            "Shoppable video comments": 10,
            "Shoppable video likes": 645,
            "Affiliate orders": 357,
            "Affiliate items sold": 367,
            "Shoppable video avg. order value": 839409,
            "GMV": 313663156,
            "Affiliate shoppable video GMV": 299669037,
            "Est. commission": 1747584,
            "Est. flat fee": "--",
            "Avg. affiliate customers": 11,
            "Affiliate items refunded": 134,
            "Affiliate refunded GMV": 119097687,
            "Shoppable video impressions": 2805923,
            "Affiliate CTR": "1%",
            "Shoppable video GPM": 98385,
        },
        {
            "Video name": "DEAL SỐC COMBO 6 LON...",
            "Video post date": "2026-02-03",
            "Creator username": "songkhoemoingay._",
            "Affiliate orders": 138,
            "GMV": 109917051,
            "Affiliate shoppable video GMV": 110218735,
            "Affiliate CTR": "1%",
        },
    ])
    content = _to_xlsx(videos, REAL / "Creator_Video_List_en.xlsx")
    assert detect_source_type("Creator_Video_List.xlsx", content) == "tiktok_affiliate_video"
    rows = parse_tiktok_affiliate_video(content)
    assert len(rows) == 2

    top = rows[0]
    assert top["creator_username"] == "songkhoemoingay._"
    assert str(top["posted_date"]) == "2026-03-28"
    assert top["linked_orders"] == 357.0
    assert top["items_sold"] == 367.0
    assert top["gmv"] == 313663156.0
    assert top["gmv_video"] == 299669037.0
    assert top["estimated_commission"] == 1747584.0
    assert top["estimated_flat_fee"] is None
    assert top["shoppable_impressions"] == 2805923.0
    assert top["linked_ctr"] == 1.0
    assert top["shoppable_gpm"] == 98385.0
    assert top["refunded_items"] == 134.0
    assert top["gmv_refunded"] == 119097687.0
    print("✓ Real creator video (English columns) OK")


def test_real_affiliate_product_english_schema():
    """Creator Product List — cột tiếng Anh."""
    products = pd.DataFrame([
        {
            "Product ID": "1734279932259763490",
            "Product name": "[COMBO 6 TẶNG 1 ] BỘT NGHỆ GẠO LỨT 420g",
            "Affiliate GMV": 778442972,
            "Est. commission": 26773270,
            "Avg. GMV per customer": 820277,
            "Affiliate orders": 949,
            "Items sold": 974,
            "Avg. affiliate customers": 30,
            "Product impressions": 6192795,
            "CTR": "1%",
            "GPM": 125701,
            "Product clicks": 61375,
            "Affiliate refunded GMV": 250338328,
            "Items refunded": 291,
            "Affiliate shoppable videos": 988,
            "Affiliate LIVE streams": 0,
        },
        {
            "Product ID": "1734488966355911970",
            "Product name": "[ Combo 2 Sản Phẩm Tặng 1 sổ tay ] BỘT NGHỆ GẠO LỨT 420g",
            "Affiliate GMV": 94960060,
            "Est. commission": 3461221,
            "Affiliate orders": 313,
            "Items sold": 320,
            "CTR": "2%",
            "GPM": 273376,
            "Affiliate shoppable videos": 583,
        },
    ])
    content = _to_xlsx(products, REAL / "Creator_Product_List_en.xlsx")
    assert detect_source_type("Creator_Product_List.xlsx", content) == "tiktok_affiliate_product"
    rows = parse_tiktok_affiliate_product(content)
    assert len(rows) == 2

    top = rows[0]
    assert top["product_id"] == "1734279932259763490"
    assert top["affiliate_gmv"] == 778442972.0
    assert top["estimated_commission"] == 26773270.0
    assert top["affiliate_orders"] == 949.0
    assert top["items_sold"] == 974.0
    assert top["product_impressions"] == 6192795.0
    assert top["ctr"] == 1.0
    assert top["gpm"] == 125701.0
    assert top["product_clicks"] == 61375.0
    assert top["shoppable_videos"] == 988.0
    assert top["live_streams"] == 0.0
    assert top["gmv_refunded"] == 250338328.0
    assert top["items_refunded"] == 291.0
    print("✓ Real affiliate product (English columns) OK")


def test_helpers():
    assert parse_datetime_tiktok("2026-05-17 05:30").year == 2026
    assert str(parse_date_flexible("2026-04-03")) == "2026-04-03"
    assert parse_vn_number("--") is None
    print("✓ Helpers OK")


if __name__ == "__main__":
    test_helpers()
    test_real_creative_usd_schema()
    test_real_creative()
    test_real_creator()
    test_real_video()
    test_real_video_english_schema()
    test_real_affiliate_product_english_schema()
    print("\n✓ All real export tests passed")
