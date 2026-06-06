"""Báo cáo Affiliate — tổng hợp creator + chi tiết video + xu hướng theo ngày."""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from date_filter import apply_date_filter


def _normalize_key(name: Optional[str]) -> str:
    if not name:
        return ""
    s = str(name).lower().strip().lstrip("@")
    s = re.sub(r"[\s._\-]+", "", s)
    return s


def _match_ad_account(creator_key: str, ad_account: Optional[str]) -> bool:
    ad_key = _normalize_key(ad_account)
    if not creator_key or not ad_key:
        return False
    return creator_key in ad_key or ad_key in creator_key


def _safe_float(val: Any) -> float:
    return float(val or 0)


def _calc_roi(gmv: float, ad_cost: float, commission: float) -> Optional[float]:
    if ad_cost > 0:
        return round(gmv / ad_cost, 2)
    if commission > 0:
        return round(gmv / commission, 2)
    return None


def _fetch_ad_by_account(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict[str, dict[str, float]]:
    q = db.query(
        models.TiktokAdCreative.tiktok_account,
        func.sum(models.TiktokAdCreative.cost).label("cost"),
        func.sum(models.TiktokAdCreative.gross_revenue).label("revenue"),
        func.count(models.TiktokAdCreative.id).label("cnt"),
    )
    if date_from or date_to:
        q = apply_date_filter(q, models.TiktokAdCreative.posted_at, date_from, date_to)
    rows = q.group_by(models.TiktokAdCreative.tiktok_account).all()

    out: dict[str, dict[str, float]] = {}
    for r in rows:
        key = _normalize_key(r.tiktok_account)
        if not key:
            continue
        out[key] = {
            "account": r.tiktok_account or "",
            "ad_cost": _safe_float(r.cost),
            "ad_revenue": _safe_float(r.revenue),
            "ad_count": _safe_float(r.cnt),
        }
    return out


def _assign_ad_cost(creator_key: str, ad_map: dict[str, dict[str, float]]) -> dict[str, float]:
    if creator_key in ad_map:
        return ad_map[creator_key]
    best: dict[str, float] = {"ad_cost": 0.0, "ad_revenue": 0.0, "ad_count": 0.0, "account": ""}
    for ad_key, data in ad_map.items():
        if _match_ad_account(creator_key, data.get("account") or ad_key):
            if data["ad_cost"] > best["ad_cost"]:
                best = {**data}
    return best


def _aggregate_creators_from_videos(
    db: Session,
    date_from: Optional[date],
    date_to: Optional[date],
) -> dict[str, dict[str, Any]]:
    """Gom creator từ bảng video — chính xác theo ngày đăng."""
    q = db.query(
        models.TiktokAffiliateVideo.creator_username,
        func.sum(models.TiktokAffiliateVideo.gmv).label("gmv"),
        func.sum(models.TiktokAffiliateVideo.linked_orders).label("orders"),
        func.sum(models.TiktokAffiliateVideo.shoppable_impressions).label("views"),
        func.sum(models.TiktokAffiliateVideo.estimated_commission).label("commission"),
        func.count(models.TiktokAffiliateVideo.id).label("video_count"),
    )
    q = apply_date_filter(q, models.TiktokAffiliateVideo.posted_date, date_from, date_to)
    rows = q.group_by(models.TiktokAffiliateVideo.creator_username).all()

    merged: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not r.creator_username:
            continue
        merged[r.creator_username] = {
            "creator_username": r.creator_username,
            "gmv": _safe_float(r.gmv),
            "views": _safe_float(r.views),
            "orders": _safe_float(r.orders),
            "commission": _safe_float(r.commission),
            "video_count": int(r.video_count or 0),
            "followers": 0.0,
        }
    return merged


def _merge_creator_list(
    db: Session,
    merged: dict[str, dict[str, Any]],
    use_list_totals: bool,
) -> None:
    """Bổ sung creator list khi không lọc ngày (export tổng kỳ)."""
    if not use_list_totals:
        # Chỉ lấy followers
        for row in db.query(models.TiktokAffiliateCreator).all():
            if not row.creator_username:
                continue
            if row.creator_username not in merged:
                merged[row.creator_username] = {
                    "creator_username": row.creator_username,
                    "gmv": 0.0, "views": 0.0, "orders": 0.0,
                    "commission": 0.0, "video_count": 0, "followers": 0.0,
                }
            merged[row.creator_username]["followers"] = max(
                merged[row.creator_username]["followers"],
                _safe_float(row.followers),
            )
        return

    creator_rows = (
        db.query(
            models.TiktokAffiliateCreator.creator_username,
            func.sum(models.TiktokAffiliateCreator.gmv).label("gmv"),
            func.sum(models.TiktokAffiliateCreator.orders).label("orders"),
            func.sum(models.TiktokAffiliateCreator.product_impressions).label("views"),
            func.sum(models.TiktokAffiliateCreator.estimated_commission).label("commission"),
            func.sum(models.TiktokAffiliateCreator.linked_videos).label("video_count"),
            func.max(models.TiktokAffiliateCreator.followers).label("followers"),
        )
        .group_by(models.TiktokAffiliateCreator.creator_username)
        .all()
    )

    for r in creator_rows:
        if not r.creator_username:
            continue
        key = r.creator_username
        if key not in merged:
            merged[key] = {
                "creator_username": key,
                "gmv": 0.0, "views": 0.0, "orders": 0.0,
                "commission": 0.0, "video_count": 0, "followers": 0.0,
            }
        rec = merged[key]
        rec["gmv"] = max(rec["gmv"], _safe_float(r.gmv))
        rec["views"] = max(rec["views"], _safe_float(r.views))
        rec["orders"] = max(rec["orders"], _safe_float(r.orders))
        rec["commission"] = max(rec["commission"], _safe_float(r.commission))
        rec["video_count"] = max(rec["video_count"], int(r.video_count or 0))
        rec["followers"] = max(rec["followers"], _safe_float(r.followers))

    video_agg = (
        db.query(
            models.TiktokAffiliateVideo.creator_username,
            func.sum(models.TiktokAffiliateVideo.gmv).label("gmv"),
            func.sum(models.TiktokAffiliateVideo.linked_orders).label("orders"),
            func.sum(models.TiktokAffiliateVideo.shoppable_impressions).label("views"),
            func.sum(models.TiktokAffiliateVideo.estimated_commission).label("commission"),
            func.count(models.TiktokAffiliateVideo.id).label("video_count"),
        )
        .group_by(models.TiktokAffiliateVideo.creator_username)
        .all()
    )
    for r in video_agg:
        if not r.creator_username:
            continue
        key = r.creator_username
        if key not in merged:
            merged[key] = {
                "creator_username": key,
                "gmv": 0.0, "views": 0.0, "orders": 0.0,
                "commission": 0.0, "video_count": 0, "followers": 0.0,
            }
        rec = merged[key]
        if rec["gmv"] == 0:
            rec["gmv"] = _safe_float(r.gmv)
        if rec["views"] == 0:
            rec["views"] = _safe_float(r.views)
        if rec["orders"] == 0:
            rec["orders"] = _safe_float(r.orders)
        if rec["commission"] == 0:
            rec["commission"] = _safe_float(r.commission)
        rec["video_count"] = max(rec["video_count"], int(r.video_count or 0))


def get_affiliate_report(
    db: Session,
    sort: str = "gmv",
    limit: int = 20,
    offset: int = 0,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict[str, Any]:
    has_date_filter = date_from is not None or date_to is not None

    if has_date_filter:
        merged = _aggregate_creators_from_videos(db, date_from, date_to)
        _merge_creator_list(db, merged, use_list_totals=False)
    else:
        merged = {}
        _merge_creator_list(db, merged, use_list_totals=True)

    ad_map = _fetch_ad_by_account(db, date_from, date_to)
    creators: list[dict[str, Any]] = []

    for rec in merged.values():
        if not rec["creator_username"]:
            continue
        if has_date_filter and rec["gmv"] == 0 and rec["video_count"] == 0:
            continue
        ck = _normalize_key(rec["creator_username"])
        ad = _assign_ad_cost(ck, ad_map)
        ad_cost = ad.get("ad_cost", 0.0)
        ad_count = int(ad.get("ad_count", 0) or 0)
        avg_ad = round(ad_cost / ad_count, 0) if ad_count > 0 else None
        gmv = rec["gmv"]
        commission = rec["commission"]
        creators.append({
            "creator_username": rec["creator_username"],
            "gmv": gmv,
            "views": rec["views"],
            "orders": rec["orders"],
            "commission": commission,
            "followers": rec["followers"],
            "video_count": rec["video_count"],
            "ad_cost_total": ad_cost,
            "ad_revenue": ad.get("ad_revenue", 0.0),
            "ad_account": ad.get("account") or None,
            "avg_ad_cost": avg_ad,
            "roi": _calc_roi(gmv, ad_cost, commission),
        })

    sort_key = {
        "gmv": lambda x: x["gmv"],
        "views": lambda x: x["views"],
        "roi": lambda x: x["roi"] if x["roi"] is not None else -1,
        "avg_ad_cost": lambda x: x["avg_ad_cost"] if x["avg_ad_cost"] is not None else -1,
        "orders": lambda x: x["orders"],
    }.get(sort, lambda x: x["gmv"])

    creators.sort(key=sort_key, reverse=True)
    total = len(creators)
    page_creators = creators[offset : offset + limit]

    all_ad = sum(c["ad_cost_total"] for c in creators)
    ad_with_cost = [c for c in creators if c["avg_ad_cost"]]

    return {
        "sort": sort,
        "offset": offset,
        "limit": limit,
        "total": total,
        "creators": page_creators,
        "summary": {
            "total_creators": total,
            "total_gmv": sum(c["gmv"] for c in creators),
            "total_views": sum(c["views"] for c in creators),
            "total_orders": sum(c["orders"] for c in creators),
            "total_ad_cost": all_ad,
            "avg_ad_cost": round(all_ad / len(ad_with_cost), 0) if ad_with_cost else None,
        },
    }


def get_affiliate_trend(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict[str, Any]:
    """Xu hướng GMV / view / đơn affiliate theo ngày đăng video."""
    q = (
        db.query(
            models.TiktokAffiliateVideo.posted_date,
            func.sum(models.TiktokAffiliateVideo.gmv).label("gmv"),
            func.sum(models.TiktokAffiliateVideo.shoppable_impressions).label("views"),
            func.sum(models.TiktokAffiliateVideo.linked_orders).label("orders"),
            func.count(models.TiktokAffiliateVideo.id).label("videos"),
        )
        .filter(models.TiktokAffiliateVideo.posted_date.isnot(None))
    )
    q = apply_date_filter(q, models.TiktokAffiliateVideo.posted_date, date_from, date_to)
    rows = q.group_by(models.TiktokAffiliateVideo.posted_date).order_by(
        models.TiktokAffiliateVideo.posted_date
    ).all()

    daily = [
        {
            "date": r.posted_date.isoformat() if r.posted_date else None,
            "gmv": _safe_float(r.gmv),
            "views": _safe_float(r.views),
            "orders": _safe_float(r.orders),
            "videos": int(r.videos or 0),
        }
        for r in rows
    ]
    return {
        "daily": daily,
        "totals": {
            "gmv": sum(d["gmv"] for d in daily),
            "views": sum(d["views"] for d in daily),
            "orders": sum(d["orders"] for d in daily),
        },
    }


def get_creator_videos(
    db: Session,
    creator_username: str,
    sort: str = "gmv",
    limit: int = 50,
    offset: int = 0,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict[str, Any]:
    q = db.query(models.TiktokAffiliateVideo).filter(
        models.TiktokAffiliateVideo.creator_username == creator_username
    )
    q = apply_date_filter(q, models.TiktokAffiliateVideo.posted_date, date_from, date_to)
    rows = q.all()

    videos: list[dict[str, Any]] = []
    for v in rows:
        gmv = _safe_float(v.gmv)
        commission = _safe_float(v.estimated_commission)
        videos.append({
            "video_name": v.video_name,
            "posted_date": v.posted_date.isoformat() if v.posted_date else None,
            "gmv": gmv,
            "gmv_video": _safe_float(v.gmv_video),
            "views": _safe_float(v.shoppable_impressions),
            "orders": _safe_float(v.linked_orders),
            "items_sold": _safe_float(v.items_sold),
            "commission": commission,
            "aov": _safe_float(v.shoppable_aov),
            "ctr": _safe_float(v.linked_ctr),
            "gpm": _safe_float(v.shoppable_gpm),
            "likes": _safe_float(v.shoppable_likes),
            "comments": _safe_float(v.shoppable_comments),
            "gmv_refunded": _safe_float(v.gmv_refunded),
            "roi": _calc_roi(gmv, 0, commission),
        })

    sort_key = {
        "gmv": lambda x: x["gmv"],
        "views": lambda x: x["views"],
        "roi": lambda x: x["roi"] if x["roi"] is not None else -1,
        "orders": lambda x: x["orders"],
    }.get(sort, lambda x: x["gmv"])

    videos.sort(key=sort_key, reverse=True)
    total = len(videos)
    all_videos = videos
    videos = videos[offset : offset + limit]

    creator_row = (
        db.query(models.TiktokAffiliateCreator)
        .filter(models.TiktokAffiliateCreator.creator_username == creator_username)
        .first()
    )
    ad_map = _fetch_ad_by_account(db, date_from, date_to)
    ad = _assign_ad_cost(_normalize_key(creator_username), ad_map)
    ad_cost = ad.get("ad_cost", 0.0)

    total_gmv = sum(v["gmv"] for v in all_videos) or _safe_float(creator_row.gmv if creator_row else 0)
    total_views = sum(v["views"] for v in all_videos) or _safe_float(
        creator_row.product_impressions if creator_row else 0
    )
    total_commission = sum(v["commission"] for v in all_videos) or _safe_float(
        creator_row.estimated_commission if creator_row else 0
    )

    return {
        "creator_username": creator_username,
        "offset": offset,
        "limit": limit,
        "total": total,
        "summary": {
            "gmv": total_gmv,
            "views": total_views,
            "orders": sum(v["orders"] for v in all_videos) or _safe_float(creator_row.orders if creator_row else 0),
            "commission": total_commission,
            "video_count": total,
            "followers": _safe_float(creator_row.followers if creator_row else 0),
            "ad_cost_total": ad_cost,
            "ad_account": ad.get("account") or None,
            "avg_ad_cost": round(ad_cost / int(ad.get("ad_count") or 0), 0) if ad.get("ad_count") else None,
            "roi": _calc_roi(total_gmv, ad_cost, total_commission),
        },
        "videos": videos,
    }
