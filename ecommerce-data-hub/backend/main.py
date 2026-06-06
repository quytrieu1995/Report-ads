"""FastAPI — API upload/báo cáo + phục vụ frontend."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

import models
from database import Base, engine, get_db
from currency import get_usd_vnd_rate
from date_filter import apply_date_filter, range_to_dict, resolve_date_range
from ingest import delete_batch, ingest_file
from migrate import init_db
from reports.affiliate import get_affiliate_report, get_affiliate_trend, get_creator_videos

# Tạo bảng + tự migrate cột mới (DB cũ không cần xóa)
init_db(engine, Base.metadata)

app = FastAPI(title="E-commerce Data Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def _dates(preset: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None):
    """Parse tham số lọc thời gian từ query."""
    d_from, d_to = resolve_date_range(preset, date_from, date_to)
    return d_from, d_to, range_to_dict(d_from, d_to)


@app.get("/")
def serve_frontend():
    """Phục vụ trang dashboard."""
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, "Không tìm thấy frontend/index.html")
    return FileResponse(index)


@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    """Upload nhiều file — trả kết quả từng file."""
    results = []
    for f in files:
        content = await f.read()
        fname = f.filename or "unknown"
        try:
            result = ingest_file(db, fname, content)
            results.append(result)
        except Exception as exc:
            results.append({
                "filename": fname,
                "status": "error",
                "message": str(exc),
            })
    return {"results": results}


@app.get("/api/batches")
def list_batches(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Danh sách lịch sử upload."""
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    total = db.query(func.count(models.UploadBatch.id)).scalar() or 0
    batches = (
        db.query(models.UploadBatch)
        .order_by(models.UploadBatch.uploaded_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "batches": [
            {
                "id": b.id,
                "filename": b.filename,
                "source_type": b.source_type,
                "platform": b.platform,
                "period_start": b.period_start.isoformat() if b.period_start else None,
                "period_end": b.period_end.isoformat() if b.period_end else None,
                "row_count": b.row_count,
                "status": b.status,
                "message": b.message,
                "uploaded_at": b.uploaded_at.isoformat() if b.uploaded_at else None,
            }
            for b in batches
        ]
    }


@app.delete("/api/batches/{batch_id}")
def remove_batch(batch_id: int, db: Session = Depends(get_db)):
    """Xoá batch và dữ liệu liên quan."""
    ok = delete_batch(db, batch_id)
    if not ok:
        raise HTTPException(404, f"Không tìm thấy batch #{batch_id}")
    return {"status": "deleted", "batch_id": batch_id}


@app.get("/api/summary")
def get_summary(
    preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """KPI tổng hợp đa sàn — có thể lọc theo thời gian."""
    d_from, d_to, dr = _dates(preset, date_from, date_to)

    order_q = db.query(func.coalesce(func.sum(models.TiktokOrder.sku_subtotal_after_discount), 0))
    order_q = apply_date_filter(order_q, models.TiktokOrder.created_time, d_from, d_to)
    tiktok_gmv = order_q.scalar() or 0

    orders_q = db.query(func.count(distinct(models.TiktokOrder.order_id))).filter(
        models.TiktokOrder.order_id.isnot(None)
    )
    orders_q = apply_date_filter(orders_q, models.TiktokOrder.created_time, d_from, d_to)
    tiktok_orders = orders_q.scalar() or 0

    ad_revenue_q = db.query(func.coalesce(func.sum(models.TiktokAdCreative.gross_revenue), 0))
    ad_revenue_q = apply_date_filter(ad_revenue_q, models.TiktokAdCreative.posted_at, d_from, d_to)
    ad_revenue = ad_revenue_q.scalar() or 0

    ad_cost_q = db.query(func.coalesce(func.sum(models.TiktokAdCreative.cost), 0))
    ad_cost_q = apply_date_filter(ad_cost_q, models.TiktokAdCreative.posted_at, d_from, d_to)
    ad_cost = ad_cost_q.scalar() or 0
    ad_roi = round(float(ad_revenue) / float(ad_cost), 2) if ad_cost and float(ad_cost) > 0 else 0

    affiliate_creators = db.query(func.count(models.TiktokAffiliateCreator.id)).scalar() or 0
    affiliate_videos_q = db.query(func.count(models.TiktokAffiliateVideo.id))
    affiliate_videos_q = apply_date_filter(affiliate_videos_q, models.TiktokAffiliateVideo.posted_date, d_from, d_to)
    affiliate_videos = affiliate_videos_q.scalar() or 0

    affiliate_products = (
        db.query(func.count(distinct(models.TiktokAffiliateProduct.product_id)))
        .filter(models.TiktokAffiliateProduct.product_id.isnot(None))
        .scalar()
    ) or 0

    shopee_sales_q = (
        db.query(func.coalesce(func.sum(models.ShopeeShopDaily.total_sales), 0))
        .filter(models.ShopeeShopDaily.order_type == "placed")
    )
    shopee_sales_q = apply_date_filter(shopee_sales_q, models.ShopeeShopDaily.stat_date, d_from, d_to)
    shopee_sales = shopee_sales_q.scalar() or 0

    shopee_orders_q = (
        db.query(func.coalesce(func.sum(models.ShopeeShopDaily.total_orders), 0))
        .filter(models.ShopeeShopDaily.order_type == "placed")
    )
    shopee_orders_q = apply_date_filter(shopee_orders_q, models.ShopeeShopDaily.stat_date, d_from, d_to)
    shopee_orders = shopee_orders_q.scalar() or 0

    shopee_visits_q = (
        db.query(func.coalesce(func.sum(models.ShopeeShopDaily.visits), 0))
        .filter(models.ShopeeShopDaily.order_type == "placed")
    )
    shopee_visits_q = apply_date_filter(shopee_visits_q, models.ShopeeShopDaily.stat_date, d_from, d_to)
    shopee_visits = shopee_visits_q.scalar() or 0

    return {
        "date_range": dr,
        "tiktok": {
            "gmv": float(tiktok_gmv),
            "orders": int(tiktok_orders),
            "ad_revenue": float(ad_revenue),
            "ad_cost": float(ad_cost),
            "ad_roi": float(ad_roi),
            "affiliate_creators": int(affiliate_creators),
            "affiliate_videos": int(affiliate_videos),
            "affiliate_products": int(affiliate_products),
        },
        "shopee": {
            "sales": float(shopee_sales),
            "orders": float(shopee_orders),
            "visits": float(shopee_visits),
        },
        "exchange_rate": get_usd_vnd_rate(),
    }


@app.get("/api/exchange-rate")
def exchange_rate():
    """Tỉ giá USD/VND hiện hành."""
    return get_usd_vnd_rate()


@app.get("/api/report/top-products")
def top_products(
    limit: int = 20,
    offset: int = 0,
    preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Top sản phẩm TikTok — loại đơn đã hủy."""
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    d_from, d_to, dr = _dates(preset, date_from, date_to)
    base = (
        db.query(
            models.TiktokOrder.seller_sku,
            models.TiktokOrder.product_name,
            func.sum(models.TiktokOrder.sku_subtotal_after_discount).label("total"),
            func.sum(models.TiktokOrder.quantity).label("qty"),
        )
        .filter(models.TiktokOrder.order_status != "Đã hủy")
    )
    base = apply_date_filter(base, models.TiktokOrder.created_time, d_from, d_to)
    base = base.group_by(models.TiktokOrder.seller_sku, models.TiktokOrder.product_name)
    subq = base.subquery()
    total = db.query(func.count()).select_from(subq).scalar() or 0
    rows = (
        base.order_by(func.sum(models.TiktokOrder.sku_subtotal_after_discount).desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "date_range": dr,
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "products": [
            {
                "seller_sku": r.seller_sku,
                "product_name": r.product_name,
                "total_sales": float(r.total or 0),
                "quantity": float(r.qty or 0),
            }
            for r in rows
        ],
    }


@app.get("/api/report/shopee-products")
def shopee_products(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Top sản phẩm Shopee theo doanh số."""
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    base = (
        db.query(
            models.ShopeeProductStat.product_id,
            models.ShopeeProductStat.product_name,
            func.sum(models.ShopeeProductStat.sales).label("sales"),
            func.sum(models.ShopeeProductStat.total_orders).label("orders"),
            func.sum(models.ShopeeProductStat.impressions).label("impressions"),
            func.sum(models.ShopeeProductStat.clicks).label("clicks"),
        )
        .group_by(models.ShopeeProductStat.product_id, models.ShopeeProductStat.product_name)
    )
    subq = base.subquery()
    total = db.query(func.count()).select_from(subq).scalar() or 0
    rows = (
        base.order_by(func.sum(models.ShopeeProductStat.sales).desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "products": [
            {
                "product_id": r.product_id,
                "product_name": r.product_name,
                "sales": float(r.sales or 0),
                "orders": float(r.orders or 0),
                "impressions": float(r.impressions or 0),
                "clicks": float(r.clicks or 0),
            }
            for r in rows
        ],
    }


@app.get("/api/report/top-creators")
def top_creators(limit: int = 10, db: Session = Depends(get_db)):
    """Top nhà sáng tạo affiliate theo GMV."""
    rows = (
        db.query(
            models.TiktokAffiliateCreator.creator_username,
            func.sum(models.TiktokAffiliateCreator.gmv).label("total_gmv"),
            func.sum(models.TiktokAffiliateCreator.orders).label("total_orders"),
        )
        .group_by(models.TiktokAffiliateCreator.creator_username)
        .order_by(func.sum(models.TiktokAffiliateCreator.gmv).desc())
        .limit(limit)
        .all()
    )
    return {
        "creators": [
            {
                "creator_username": r.creator_username,
                "gmv": float(r.total_gmv or 0),
                "orders": float(r.total_orders or 0),
            }
            for r in rows
        ]
    }


@app.get("/api/report/shopee-daily")
def shopee_daily(
    order_type: str = "placed",
    limit: int = 100,
    offset: int = 0,
    preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Doanh số Shopee theo ngày."""
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    d_from, d_to, dr = _dates(preset, date_from, date_to)
    base = (
        db.query(
            models.ShopeeShopDaily.stat_date,
            func.sum(models.ShopeeShopDaily.total_sales).label("sales"),
            func.sum(models.ShopeeShopDaily.total_orders).label("orders"),
            func.sum(models.ShopeeShopDaily.visits).label("visits"),
        )
        .filter(models.ShopeeShopDaily.order_type == order_type)
    )
    base = apply_date_filter(base, models.ShopeeShopDaily.stat_date, d_from, d_to)
    base = base.group_by(models.ShopeeShopDaily.stat_date)
    subq = base.subquery()
    total = db.query(func.count()).select_from(subq).scalar() or 0
    rows = base.order_by(models.ShopeeShopDaily.stat_date).offset(offset).limit(limit).all()
    return {
        "date_range": dr,
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "daily": [
            {
                "date": r.stat_date.isoformat() if r.stat_date else None,
                "sales": float(r.sales or 0),
                "orders": float(r.orders or 0),
                "visits": float(r.visits or 0),
            }
            for r in rows
        ],
    }


@app.get("/api/report/affiliate")
def affiliate_report(
    sort: str = "gmv",
    limit: int = 20,
    offset: int = 0,
    preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    allowed = {"gmv", "views", "roi", "avg_ad_cost", "orders"}
    if sort not in allowed:
        raise HTTPException(400, f"sort phải là một trong: {', '.join(sorted(allowed))}")
    d_from, d_to, dr = _dates(preset, date_from, date_to)
    result = get_affiliate_report(
        db, sort=sort, limit=min(max(limit, 1), 100), offset=max(offset, 0),
        date_from=d_from, date_to=d_to,
    )
    result["date_range"] = dr
    return result


@app.get("/api/report/affiliate-trend")
def affiliate_trend(
    preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Biểu đồ xu hướng affiliate GMV/view/đơn theo ngày."""
    d_from, d_to, dr = _dates(preset, date_from, date_to)
    result = get_affiliate_trend(db, date_from=d_from, date_to=d_to)
    result["date_range"] = dr
    return result


@app.get("/api/report/affiliate-products")
def affiliate_products(
    sort: str = "gmv",
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Top sản phẩm affiliate — gộp theo product_id."""
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    allowed = {"gmv", "orders", "commission", "impressions", "ctr", "gpm", "videos"}
    if sort not in allowed:
        raise HTTPException(400, f"sort phải là một trong: {', '.join(sorted(allowed))}")

    P = models.TiktokAffiliateProduct
    base = db.query(
        P.product_id,
        func.max(P.product_name).label("product_name"),
        func.sum(P.affiliate_gmv).label("gmv"),
        func.sum(P.estimated_commission).label("commission"),
        func.sum(P.affiliate_orders).label("orders"),
        func.sum(P.items_sold).label("items_sold"),
        func.sum(P.product_impressions).label("impressions"),
        func.sum(P.product_clicks).label("clicks"),
        func.sum(P.shoppable_videos).label("videos"),
        func.sum(P.live_streams).label("live_streams"),
        func.sum(P.gmv_refunded).label("gmv_refunded"),
        func.avg(P.ctr).label("ctr"),
        func.avg(P.gpm).label("gpm"),
    ).filter(P.product_id.isnot(None)).group_by(P.product_id)

    sort_map = {
        "gmv": func.sum(P.affiliate_gmv).desc(),
        "orders": func.sum(P.affiliate_orders).desc(),
        "commission": func.sum(P.estimated_commission).desc(),
        "impressions": func.sum(P.product_impressions).desc(),
        "ctr": func.avg(P.ctr).desc(),
        "gpm": func.avg(P.gpm).desc(),
        "videos": func.sum(P.shoppable_videos).desc(),
    }
    subq = base.subquery()
    total = db.query(func.count()).select_from(subq).scalar() or 0
    rows = base.order_by(sort_map[sort]).offset(offset).limit(limit).all()

    return {
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "products": [
            {
                "product_id": r.product_id,
                "product_name": r.product_name,
                "gmv": float(r.gmv or 0),
                "commission": float(r.commission or 0),
                "orders": float(r.orders or 0),
                "items_sold": float(r.items_sold or 0),
                "impressions": float(r.impressions or 0),
                "clicks": float(r.clicks or 0),
                "videos": float(r.videos or 0),
                "live_streams": float(r.live_streams or 0),
                "gmv_refunded": float(r.gmv_refunded or 0),
                "ctr": float(r.ctr) if r.ctr is not None else None,
                "gpm": float(r.gpm) if r.gpm is not None else None,
            }
            for r in rows
        ],
    }


@app.get("/api/report/affiliate/{creator_username}/videos")
def affiliate_creator_videos(
    creator_username: str,
    sort: str = "gmv",
    limit: int = 20,
    offset: int = 0,
    preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    allowed = {"gmv", "views", "roi", "orders"}
    if sort not in allowed:
        raise HTTPException(400, f"sort phải là một trong: {', '.join(sorted(allowed))}")
    d_from, d_to, dr = _dates(preset, date_from, date_to)
    result = get_creator_videos(
        db,
        creator_username,
        sort=sort,
        limit=min(max(limit, 1), 100),
        offset=max(offset, 0),
        date_from=d_from,
        date_to=d_to,
    )
    result["date_range"] = dr
    if not result["videos"] and not result["summary"]["gmv"]:
        raise HTTPException(404, f"Không tìm thấy creator: {creator_username}")
    return result
