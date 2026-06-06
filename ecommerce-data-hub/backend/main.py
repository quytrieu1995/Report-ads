"""FastAPI — API upload/báo cáo + phục vụ frontend."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

import models
from database import Base, engine, get_db
from currency import get_usd_vnd_rate
from ingest import delete_batch, ingest_file
from migrate import init_db
from reports.affiliate import get_affiliate_report, get_creator_videos

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
def get_summary(db: Session = Depends(get_db)):
    """KPI tổng hợp đa sàn."""
    # TikTok GMV & số đơn (distinct order_id)
    tiktok_gmv = (
        db.query(func.coalesce(func.sum(models.TiktokOrder.sku_subtotal_after_discount), 0))
        .scalar()
    ) or 0
    tiktok_orders = (
        db.query(func.count(distinct(models.TiktokOrder.order_id)))
        .filter(models.TiktokOrder.order_id.isnot(None))
        .scalar()
    ) or 0

    # ROI quảng cáo = Σ doanh thu / Σ chi phí
    ad_revenue = db.query(func.coalesce(func.sum(models.TiktokAdCreative.gross_revenue), 0)).scalar() or 0
    ad_cost = db.query(func.coalesce(func.sum(models.TiktokAdCreative.cost), 0)).scalar() or 0
    ad_roi = round(ad_revenue / ad_cost, 2) if ad_cost > 0 else 0

    affiliate_creators = db.query(func.count(models.TiktokAffiliateCreator.id)).scalar() or 0
    affiliate_videos = db.query(func.count(models.TiktokAffiliateVideo.id)).scalar() or 0

    # Shopee — chỉ order_type='placed'
    shopee_sales = (
        db.query(func.coalesce(func.sum(models.ShopeeShopDaily.total_sales), 0))
        .filter(models.ShopeeShopDaily.order_type == "placed")
        .scalar()
    ) or 0
    shopee_orders = (
        db.query(func.coalesce(func.sum(models.ShopeeShopDaily.total_orders), 0))
        .filter(models.ShopeeShopDaily.order_type == "placed")
        .scalar()
    ) or 0
    shopee_visits = (
        db.query(func.coalesce(func.sum(models.ShopeeShopDaily.visits), 0))
        .filter(models.ShopeeShopDaily.order_type == "placed")
        .scalar()
    ) or 0

    return {
        "tiktok": {
            "gmv": float(tiktok_gmv),
            "orders": int(tiktok_orders),
            "ad_revenue": float(ad_revenue),
            "ad_cost": float(ad_cost),
            "ad_roi": float(ad_roi),
            "affiliate_creators": int(affiliate_creators),
            "affiliate_videos": int(affiliate_videos),
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
    db: Session = Depends(get_db),
):
    """Top sản phẩm TikTok — loại đơn đã hủy."""
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    base = (
        db.query(
            models.TiktokOrder.seller_sku,
            models.TiktokOrder.product_name,
            func.sum(models.TiktokOrder.sku_subtotal_after_discount).label("total"),
            func.sum(models.TiktokOrder.quantity).label("qty"),
        )
        .filter(models.TiktokOrder.order_status != "Đã hủy")
        .group_by(models.TiktokOrder.seller_sku, models.TiktokOrder.product_name)
    )
    subq = base.subquery()
    total = db.query(func.count()).select_from(subq).scalar() or 0
    rows = (
        base.order_by(func.sum(models.TiktokOrder.sku_subtotal_after_discount).desc())
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
    db: Session = Depends(get_db),
):
    """Doanh số Shopee theo ngày."""
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    base = (
        db.query(
            models.ShopeeShopDaily.stat_date,
            func.sum(models.ShopeeShopDaily.total_sales).label("sales"),
            func.sum(models.ShopeeShopDaily.total_orders).label("orders"),
            func.sum(models.ShopeeShopDaily.visits).label("visits"),
        )
        .filter(models.ShopeeShopDaily.order_type == order_type)
        .group_by(models.ShopeeShopDaily.stat_date)
    )
    subq = base.subquery()
    total = db.query(func.count()).select_from(subq).scalar() or 0
    rows = base.order_by(models.ShopeeShopDaily.stat_date).offset(offset).limit(limit).all()
    return {
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
    db: Session = Depends(get_db),
):
    """
    Báo cáo Affiliate — xếp hạng creator.
    sort: gmv | views | roi | avg_ad_cost | orders
    """
    allowed = {"gmv", "views", "roi", "avg_ad_cost", "orders"}
    if sort not in allowed:
        raise HTTPException(400, f"sort phải là một trong: {', '.join(sorted(allowed))}")
    return get_affiliate_report(
        db, sort=sort, limit=min(max(limit, 1), 100), offset=max(offset, 0)
    )


@app.get("/api/report/affiliate/{creator_username}/videos")
def affiliate_creator_videos(
    creator_username: str,
    sort: str = "gmv",
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Chi tiết video affiliate của một creator."""
    allowed = {"gmv", "views", "roi", "orders"}
    if sort not in allowed:
        raise HTTPException(400, f"sort phải là một trong: {', '.join(sorted(allowed))}")
    result = get_creator_videos(
        db,
        creator_username,
        sort=sort,
        limit=min(max(limit, 1), 100),
        offset=max(offset, 0),
    )
    if not result["videos"] and not result["summary"]["gmv"]:
        raise HTTPException(404, f"Không tìm thấy creator: {creator_username}")
    return result
