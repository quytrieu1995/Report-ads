"""Nhận diện loại file, chuẩn hoá dữ liệu và parse từng nguồn."""
from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Helper chuẩn hoá dữ liệu (dùng chung)
# ---------------------------------------------------------------------------

EMPTY_MARKERS = {"", "-", "--", "nan", "none", "null", "n/a"}


def clean_value(val: Any) -> Any:
    """Ô rỗng / nan / '-' → None."""
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    s = str(val).strip()
    if s.lower() in EMPTY_MARKERS:
        return None
    return val


def parse_id_string(val: Any) -> str | None:
    """ID lớn lưu dạng chuỗi — bỏ tab, đuôi .0 do pandas."""
    v = clean_value(val)
    if v is None:
        return None
    s = str(v).strip().replace("\t", "")
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    # Tránh scientific notation
    if "e" in s.lower() and re.match(r"^[\d.]+e[+-]?\d+$", s, re.I):
        try:
            s = str(int(float(s)))
        except (ValueError, OverflowError):
            pass
    return s or None


def parse_vn_number(val: Any) -> float | None:
    """
    Parse số kiểu Việt Nam:
    - '.' phân tách nghìn, ',' thập phân
    - '3.293.607.217' → 3293607217.0
    - '333.834,10' → 333834.10
    """
    v = clean_value(val)
    if v is None:
        return None
    if isinstance(v, (int, float)) and not (isinstance(v, float) and pd.isna(v)):
        return float(v)

    s = str(v).strip().replace("\t", "").replace(" ", "")
    s = s.replace("%", "")

    if not s:
        return None

    # Chỉ có dấu phẩy với ≤2 chữ số sau → thập phân
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = parts[0] + "." + parts[1]
            try:
                return float(s)
            except ValueError:
                return None

    # Có cả . và ,
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    # Nhiều dấu chấm → phân tách nghìn
    if s.count(".") > 1:
        s = s.replace(".", "")
        try:
            return float(s)
        except ValueError:
            return None

    # Một dấu chấm — có thể thập phân hoặc nghìn
    if s.count(".") == 1:
        parts = s.split(".")
        if len(parts[1]) <= 2:
            try:
                return float(s)
            except ValueError:
                return None
        s = s.replace(".", "")
        try:
            return float(s)
        except ValueError:
            return None

    try:
        return float(s)
    except ValueError:
        return None


def parse_percent(val: Any) -> float | None:
    """'7,34%' → 7.34 (không chia 100)."""
    v = clean_value(val)
    if v is None:
        return None
    s = str(v).strip().replace("\t", "")
    has_pct = "%" in s
    s = s.replace("%", "")
    num = parse_vn_number(s)
    if num is None:
        return None
    return num


def parse_datetime_tiktok(val: Any) -> datetime | None:
    """TikTok: dd/mm/yyyy hoặc yyyy-mm-dd HH:MM — strip tab trước khi parse."""
    v = clean_value(val)
    if v is None:
        return None
    if isinstance(v, (datetime, pd.Timestamp)):
        return v.to_pydatetime() if isinstance(v, pd.Timestamp) else v
    s = str(v).strip().replace("\t", "")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_date_flexible(val: Any) -> date | None:
    """Ngày linh hoạt: yyyy-mm-dd (TikTok affiliate) hoặc dd-mm-yyyy (Shopee)."""
    v = clean_value(val)
    if v is None:
        return None
    if isinstance(v, (datetime, pd.Timestamp)):
        return v.date() if hasattr(v, "date") else v
    s = str(v).strip()
    if re.match(r"\d{2}-\d{2}-\d{4}-\d{2}-\d{2}-\d{4}", s):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_date_shopee(val: Any) -> date | None:
    """Shopee: dd-mm-yyyy — trả None nếu là range hoặc không parse được."""
    return parse_date_flexible(val)


def extract_period_from_filename(filename: str) -> tuple[date | None, date | None]:
    """Suy ra period_start/end từ tên file."""
    # YYYYMMDD-YYYYMMDD
    m = re.search(r"(\d{8})-(\d{8})", filename)
    if m:
        try:
            start = datetime.strptime(m.group(1), "%Y%m%d").date()
            end = datetime.strptime(m.group(2), "%Y%m%d").date()
            return start, end
        except ValueError:
            pass
    # YYYY-MM-DD hoặc YYYY-MM-DD_YYYY-MM-DD
    m = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if m:
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            return d, d
        except ValueError:
            pass
    m = re.findall(r"(\d{4}-\d{2}-\d{2})", filename)
    if len(m) >= 2:
        try:
            return (
                datetime.strptime(m[0], "%Y-%m-%d").date(),
                datetime.strptime(m[1], "%Y-%m-%d").date(),
            )
        except ValueError:
            pass
    return None, None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace tên cột."""
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _row_to_dict(row: pd.Series, mapping: dict[str, str], transforms: dict[str, Any]) -> dict:
    """Map cột gốc → snake_case và áp transform."""
    out: dict[str, Any] = {}
    for src_col, dst_col in mapping.items():
        raw = row.get(src_col) if src_col in row.index else None
        fn = transforms.get(dst_col, clean_value)
        out[dst_col] = fn(raw)
    return out


# ---------------------------------------------------------------------------
# Nhận diện loại file
# ---------------------------------------------------------------------------

def detect_source_type(filename: str, content: bytes) -> str:
    """Tự nhận diện nguồn dữ liệu qua tên cột / sheet."""
    lower = filename.lower()

    if lower.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", nrows=5)
            cols = {str(c).strip() for c in df.columns}
            if "Order ID" in cols and "Seller SKU" in cols:
                return "tiktok_order"
        except Exception:
            pass

    if lower.endswith((".xlsx", ".xls")):
        try:
            xl = pd.ExcelFile(io.BytesIO(content))
            for sheet in xl.sheet_names:
                if sheet.strip() in ("Đơn hàng đã đặt", "Đơn đã xác nhận", "Đơn Đã Thanh Toán"):
                    return "shopee_shop"
            # Đọc sheet đầu để kiểm tra cột
            df = pd.read_excel(io.BytesIO(content), nrows=5)
            cols = {str(c).strip() for c in df.columns}
            if "Tổng doanh số (VND)" in cols:
                return "shopee_shop"
            if "ID video" in cols and "Loại nội dung sáng tạo" in cols:
                return "tiktok_ad_creative"
            if "Tên video" in cols and "Tên người dùng của nhà sáng tạo" in cols:
                return "tiktok_affiliate_video"
            if "Tên người dùng của nhà sáng tạo" in cols and "GMV liên kết" in cols:
                if "Tên video" not in cols:
                    return "tiktok_affiliate_creator"
        except Exception:
            pass

    raise ValueError(f"Không nhận diện được loại file: {filename}")


# ---------------------------------------------------------------------------
# Parser từng nguồn
# ---------------------------------------------------------------------------

TIKTOK_ORDER_MAP = {
    "Order ID": "order_id",
    "Order Status": "order_status",
    "Order Substatus": "order_substatus",
    "Cancelation/Return Type": "cancelation_return_type",
    "SKU ID": "sku_id",
    "Seller SKU": "seller_sku",
    "Product Name": "product_name",
    "Variation": "variation",
    "Quantity": "quantity",
    "Sku Quantity of return": "sku_quantity_of_return",
    "SKU Unit Original Price": "sku_unit_original_price",
    "SKU Subtotal Before Discount": "sku_subtotal_before_discount",
    "SKU Platform Discount": "sku_platform_discount",
    "SKU Seller Discount": "sku_seller_discount",
    "SKU Subtotal After Discount": "sku_subtotal_after_discount",
    "Shipping Fee After Discount": "shipping_fee_after_discount",
    "Original Shipping Fee": "original_shipping_fee",
    "Taxes": "taxes",
    "Order Amount": "order_amount",
    "Order Refund Amount": "order_refund_amount",
    "Created Time": "created_time",
    "Paid Time": "paid_time",
    "Shipped Time": "shipped_time",
    "Delivered Time": "delivered_time",
    "Cancelled Time": "cancelled_time",
    "Cancel Reason": "cancel_reason",
    "Fulfillment Type": "fulfillment_type",
    "Warehouse Name": "warehouse_name",
    "Delivery Option": "delivery_option",
    "Shipping Provider Name": "shipping_provider_name",
    "Buyer Username": "buyer_username",
    "Province": "province",
    "District": "district",
    "Payment Method": "payment_method",
    "Weight(kg)": "weight_kg",
    "Product Category": "product_category",
}

TIKTOK_ORDER_TRANSFORMS = {
    "order_id": parse_id_string,
    "sku_id": parse_id_string,
    "seller_sku": parse_id_string,
    "quantity": parse_vn_number,
    "sku_quantity_of_return": parse_vn_number,
    "sku_unit_original_price": parse_vn_number,
    "sku_subtotal_before_discount": parse_vn_number,
    "sku_platform_discount": parse_vn_number,
    "sku_seller_discount": parse_vn_number,
    "sku_subtotal_after_discount": parse_vn_number,
    "shipping_fee_after_discount": parse_vn_number,
    "original_shipping_fee": parse_vn_number,
    "taxes": parse_vn_number,
    "order_amount": parse_vn_number,
    "order_refund_amount": parse_vn_number,
    "weight_kg": parse_vn_number,
    "created_time": parse_datetime_tiktok,
    "paid_time": parse_datetime_tiktok,
    "shipped_time": parse_datetime_tiktok,
    "delivered_time": parse_datetime_tiktok,
    "cancelled_time": parse_datetime_tiktok,
}


def parse_tiktok_order(content: bytes) -> list[dict]:
    """Parse CSV đơn hàng TikTok — cấp dòng SKU."""
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str)
    df = _normalize_columns(df)
    rows = []
    for _, row in df.iterrows():
        if clean_value(row.get("Order ID")) is None:
            continue
        rows.append(_row_to_dict(row, TIKTOK_ORDER_MAP, TIKTOK_ORDER_TRANSFORMS))
    return rows


TIKTOK_AD_MAP = {
    "ID video": "video_id",
    "Tiêu đề video": "video_title",
    "Tài khoản TikTok": "tiktok_account",
    "Loại nội dung sáng tạo": "creative_type",
    "Nguồn video": "video_source",
    "Trạng thái": "status",
    "Thời gian đăng": "posted_at",
    "Chi phí": "cost",
    "Số lượng đơn hàng SKU": "sku_order_count",
    "Chi phí cho mỗi đơn hàng": "cost_per_order",
    "Doanh thu gộp": "gross_revenue",
    "ROI": "roi",
    "Số lượt hiển thị quảng cáo sản phẩm": "product_ad_impressions",
    "Số lượt nhấp vào quảng cáo sản phẩm": "product_ad_clicks",
    "Tỷ lệ nhấp vào quảng cáo sản phẩm": "product_ad_ctr",
    "Tỷ lệ chuyển đổi quảng cáo": "ad_conversion_rate",
    "Tỷ lệ xem video quảng cáo trong 2 giây": "view_rate_2s",
    "Tỷ lệ xem video quảng cáo trong 6 giây": "view_rate_6s",
    "Tỷ lệ xem 25% thời lượng video quảng cáo": "view_rate_25pct",
    "Tỷ lệ xem 50% thời lượng video quảng cáo": "view_rate_50pct",
    "Tỷ lệ xem 75% thời lượng video quảng cáo": "view_rate_75pct",
    "Tỷ lệ xem 100% thời lượng video quảng cáo": "view_rate_100pct",
    "Đơn vị tiền tệ": "currency",
}

TIKTOK_AD_TRANSFORMS = {
    "video_id": parse_id_string,
    "posted_at": parse_datetime_tiktok,
    "cost": parse_vn_number,
    "sku_order_count": parse_vn_number,
    "cost_per_order": parse_vn_number,
    "gross_revenue": parse_vn_number,
    "roi": parse_vn_number,
    "product_ad_impressions": parse_vn_number,
    "product_ad_clicks": parse_vn_number,
    "product_ad_ctr": parse_percent,
    "ad_conversion_rate": parse_percent,
    "view_rate_2s": parse_percent,
    "view_rate_6s": parse_percent,
    "view_rate_25pct": parse_percent,
    "view_rate_50pct": parse_percent,
    "view_rate_75pct": parse_percent,
    "view_rate_100pct": parse_percent,
}


def parse_tiktok_ad_creative(content: bytes) -> list[dict]:
    """Parse xlsx hiệu suất video quảng cáo (gồm cả Thẻ sản phẩm, ID video = N/A)."""
    df = pd.read_excel(
        io.BytesIO(content),
        dtype={"ID video": str},
        engine="openpyxl",
    )
    df = _normalize_columns(df)
    rows = []
    for _, row in df.iterrows():
        rec = _row_to_dict(row, TIKTOK_AD_MAP, TIKTOK_AD_TRANSFORMS)
        # Giữ dòng Thẻ sản phẩm (video_id = None) nếu có số liệu chi phí/doanh thu
        if rec.get("video_id") is None:
            if rec.get("cost") is None and rec.get("gross_revenue") is None:
                continue
        rows.append(rec)
    return rows


AFFILIATE_CREATOR_MAP = {
    "Tên người dùng của nhà sáng tạo": "creator_username",
    "GMV liên kết": "gmv",
    "GMV LIVE của liên kết": "gmv_live",
    "GMV video link bán hàng của liên kết": "gmv_video",
    "GMV thẻ sản phẩm của liên kết": "gmv_product_card",
    "Sản phẩm liên kết đã bán": "linked_products_sold",
    "Số món bán ra": "items_sold",
    "Hoa hồng ước tính": "estimated_commission",
    "Phí cố định ước tính": "estimated_flat_fee",
    "Giá trị đơn hàng trung bình": "aov",
    "Trang trưng bày sản phẩm liên kết": "linked_product_showcase",
    "Đơn hàng liên kết": "orders",
    "Tỷ lệ nhấp (CTR)": "ctr",
    "Lượt hiển thị sản phẩm": "product_impressions",
    "Khách hàng liên kết trung bình": "avg_linked_customers",
    "Buổi LIVE liên kết": "linked_live_sessions",
    "Video link bán hàng của liên kết": "linked_videos",
    # Export mới (2026): tách cộng tác mục tiêu / mở
    "GMV cộng tác mục tiêu": "gmv_collab_target",
    "Hoa hồng ước tính trong cộng tác mục tiêu": "commission_collab_target",
    "GMV cộng tác mở": "gmv_collab_open",
    "Hoa hồng ước tính của cộng tác mở": "commission_collab_open",
    # Export cũ (tên dài)
    "GMV cộng tác mục tiêu/mở rộng của liên kết": "gmv_collab",
    "GMV đã hoàn tiền từ liên kết": "gmv_refunded",
    "Mặt hàng từ liên kết đã hoàn tiền": "refunded_items",
    "Người theo dõi của liên kết": "followers",
}

_NUM = parse_vn_number
_PCT = parse_percent

AFFILIATE_CREATOR_TRANSFORMS = {
    k: _NUM
    for k in AFFILIATE_CREATOR_MAP.values()
    if k not in ("creator_username",)
}
AFFILIATE_CREATOR_TRANSFORMS["ctr"] = _PCT


def parse_tiktok_affiliate_creator(content: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    df = _normalize_columns(df)
    rows = []
    for _, row in df.iterrows():
        if clean_value(row.get("Tên người dùng của nhà sáng tạo")) is None:
            continue
        rec = _row_to_dict(row, AFFILIATE_CREATOR_MAP, AFFILIATE_CREATOR_TRANSFORMS)
        # Tổng GMV cộng tác nếu export mới không có cột cũ
        if rec.get("gmv_collab") is None:
            target = rec.get("gmv_collab_target") or 0
            open_ = rec.get("gmv_collab_open") or 0
            if target or open_:
                rec["gmv_collab"] = target + open_
        rows.append(rec)
    return rows


AFFILIATE_VIDEO_MAP = {
    "Tên video": "video_name",
    "Ngày đăng video": "posted_date",
    "Tên người dùng của nhà sáng tạo": "creator_username",
    "Bình luận của video link bán hàng": "shoppable_comments",
    "Lượt thích của video link bán hàng": "shoppable_likes",
    "Đơn hàng liên kết": "linked_orders",
    "Số món bán ra qua liên kết ": "items_sold",
    "Giá trị đơn hàng trung bình của video link bán hàng": "shoppable_aov",
    "GMV": "gmv",
    "GMV video link bán hàng của liên kết": "gmv_video",
    "Hoa hồng ước tính": "estimated_commission",
    "Phí cố định ước tính": "estimated_flat_fee",
    "Khách hàng liên kết trung bình": "avg_linked_customers",
    "Mặt hàng từ liên kết đã hoàn tiền": "refunded_items",
    "GMV đã hoàn tiền từ liên kết": "gmv_refunded",
    "Lượt hiển thị của video link bán hàng": "shoppable_impressions",
    "CTR của liên kết": "linked_ctr",
    "GPM của video link bán hàng": "shoppable_gpm",
}

AFFILIATE_VIDEO_TRANSFORMS = {
    k: _NUM for k in AFFILIATE_VIDEO_MAP.values() if k not in ("video_name", "creator_username", "posted_date")
}
AFFILIATE_VIDEO_TRANSFORMS["posted_date"] = parse_date_flexible
AFFILIATE_VIDEO_TRANSFORMS["linked_ctr"] = _PCT


def parse_tiktok_affiliate_video(content: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    df = _normalize_columns(df)
    # Cột có thể có/không dấu cách cuối
    for col in list(df.columns):
        if col.strip() == "Số món bán ra qua liên kết":
            if col != "Số món bán ra qua liên kết ":
                df = df.rename(columns={col: "Số món bán ra qua liên kết "})
    rows = []
    for _, row in df.iterrows():
        if clean_value(row.get("Tên video")) is None:
            continue
        rows.append(_row_to_dict(row, AFFILIATE_VIDEO_MAP, AFFILIATE_VIDEO_TRANSFORMS))
    return rows


# Shopee sheet mapping
SHOPEE_DAILY_SHEETS = {
    "Đơn hàng đã đặt": "placed",
    "Đơn đã xác nhận": "confirmed",
    "Đơn Đã Thanh Toán": "paid",
}

SHOPEE_DAILY_COL_MAP = {
    "Ngày": "stat_date",
    "Tổng doanh số (VND)": "total_sales",
    "Doanh số không bao gồm trợ giá bởi Shopee": "sales_excl_subsidy",
    "Tổng số đơn hàng": "total_orders",
    "Doanh số trên mỗi đơn hàng": "sales_per_order",
    "Lượt nhấp vào sản phẩm": "product_clicks",
    "Số lượt truy cập": "visits",
    "Tỷ lệ chuyển đổi đơn hàng": "conversion_rate",
    "Đơn đã hủy": "cancelled_orders",
    "Doanh số đơn hủy": "cancelled_sales",
    "Đơn đã hoàn trả / hoàn tiền": "return_orders",
    "Doanh số các đơn Trả hàng/Hoàn tiền": "return_sales",
    "số người mua": "buyers",
    "số người mua mới": "new_buyers",
    "số người mua hiện tại": "existing_buyers",
    "số người mua tiềm năng": "potential_buyers",
    "Tỉ lệ quay lại của người mua": "buyer_return_rate",
}

SHOPEE_DAILY_TRANSFORMS = {
    "stat_date": parse_date_shopee,
    "total_sales": parse_vn_number,
    "sales_excl_subsidy": parse_vn_number,
    "total_orders": parse_vn_number,
    "sales_per_order": parse_vn_number,
    "product_clicks": parse_vn_number,
    "visits": parse_vn_number,
    "conversion_rate": parse_percent,
    "cancelled_orders": parse_vn_number,
    "cancelled_sales": parse_vn_number,
    "return_orders": parse_vn_number,
    "return_sales": parse_vn_number,
    "buyers": parse_vn_number,
    "new_buyers": parse_vn_number,
    "existing_buyers": parse_vn_number,
    "potential_buyers": parse_vn_number,
    "buyer_return_rate": parse_percent,
}

SHOPEE_PRODUCT_FIELDS = [
    ("Mã sản phẩm", "product_id", parse_id_string),
    ("Sản phẩm", "product_name", clean_value),
    ("Tình trạng", "status", clean_value),
    ("Tỷ lệ doanh số", "sales_ratio", parse_percent),
    ("Doanh số (VND)", "sales", parse_vn_number),
    ("Lượt hiển thị", "impressions", parse_vn_number),
    ("Lượt nhấp", "clicks", parse_vn_number),
    ("Tổng số đơn hàng", "total_orders", parse_vn_number),
    ("CTR", "ctr", parse_percent),
    ("Tỷ lệ chuyển đổi", "conversion_rate", parse_percent),
    ("Doanh số/đơn", "sales_per_order", parse_vn_number),
    ("Người mua", "buyers", parse_vn_number),
]

def _parse_shopee_daily_sheet(df_raw: pd.DataFrame, order_type: str) -> list[dict]:
    """Lọc chỉ dòng ngày đơn (dd-mm-yyyy), bỏ tổng kỳ và header lặp."""
    df = _normalize_columns(df_raw)
    rows = []
    for _, row in df.iterrows():
        d = parse_date_shopee(row.get("Ngày"))
        if d is None:
            continue
        rec = _row_to_dict(row, SHOPEE_DAILY_COL_MAP, SHOPEE_DAILY_TRANSFORMS)
        rec["order_type"] = order_type
        rows.append(rec)
    return rows


def _parse_shopee_product_sheet(content: bytes, sheet_name: str) -> list[dict]:
    """Đọc sheet sản phẩm — tìm header 'Mã sản phẩm'."""
    df_raw = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name, header=None, engine="openpyxl")
    header_row = None
    for i, row in df_raw.iterrows():
        first = clean_value(row.iloc[0])
        if first and str(first).strip() == "Mã sản phẩm":
            header_row = i
            break
    if header_row is None:
        return []

    df = pd.read_excel(
        io.BytesIO(content),
        sheet_name=sheet_name,
        header=header_row,
        engine="openpyxl",
    )
    df = _normalize_columns(df)
    # Cột "Sản phẩm" thứ hai (số lượng items) — pandas thêm hậu tố .1
    items_col = None
    sp_cols = [c for c in df.columns if str(c).startswith("Sản phẩm")]
    if len(sp_cols) >= 2:
        items_col = sp_cols[1]

    rows = []
    for _, row in df.iterrows():
        pid = parse_id_string(row.get("Mã sản phẩm"))
        if pid is None or not pid.isdigit():
            continue
        rec: dict[str, Any] = {}
        for src, dst, fn in SHOPEE_PRODUCT_FIELDS:
            rec[dst] = fn(row.get(src))
        if items_col:
            rec["items"] = parse_vn_number(row.get(items_col))
        rows.append(rec)
    return rows


def parse_shopee_shop(content: bytes) -> dict[str, list[dict]]:
    """Parse file Shopee nhiều sheet — trả daily + product."""
    xl = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
    daily_rows: list[dict] = []
    product_rows: list[dict] = []

    for sheet in xl.sheet_names:
        sn = sheet.strip()
        if sn in SHOPEE_DAILY_SHEETS:
            df = pd.read_excel(io.BytesIO(content), sheet_name=sheet, engine="openpyxl")
            daily_rows.extend(_parse_shopee_daily_sheet(df, SHOPEE_DAILY_SHEETS[sn]))
        elif sn.startswith("Theo sản phẩm") or "sản phẩm" in sn.lower():
            product_rows.extend(_parse_shopee_product_sheet(content, sheet))

    return {"daily": daily_rows, "product": product_rows}


# ---------------------------------------------------------------------------
# Registry parser
# ---------------------------------------------------------------------------

PLATFORM_MAP = {
    "tiktok_order": "tiktok",
    "tiktok_ad_creative": "tiktok",
    "tiktok_affiliate_creator": "tiktok",
    "tiktok_affiliate_video": "tiktok",
    "shopee_shop": "shopee",
}

PARSERS = {
    "tiktok_order": parse_tiktok_order,
    "tiktok_ad_creative": parse_tiktok_ad_creative,
    "tiktok_affiliate_creator": parse_tiktok_affiliate_creator,
    "tiktok_affiliate_video": parse_tiktok_affiliate_video,
    "shopee_shop": parse_shopee_shop,
}


def parse_file(source_type: str, content: bytes) -> list[dict] | dict[str, list[dict]]:
    """Gọi parser tương ứng."""
    parser = PARSERS.get(source_type)
    if not parser:
        raise ValueError(f"Không có parser cho: {source_type}")
    return parser(content)
