"""Báo cáo Affiliate — tổng hợp creator + chi tiết video."""
from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

import models


def _normalize_key(name: Optional[str]) -> str:
    """Chuẩn hoá tên để ghép creator ↔ tài khoản quảng cáo."""
    if not name:
        return ""
    s = str(name).lower().strip().lstrip("@")
    s = re.sub(r"[\s._\-]+", "", s)
    return s


def _match_ad_account(creator_key: str, ad_account: Optional[str]) -> bool:
    """Ghép creator username với Tài khoản TikTok trong Creative data."""
    ad_key = _normalize_key(ad_account)
    if not creator_key or not ad_key:
        return False
    return creator_key in ad_key or ad_key in creator_key


def _safe_float(val: Any) -> float:
    return float(val or 0)


def _calc_roi(gmv: float, ad_cost: float, commission: float) -> Optional[float]:
    """ROI = GMV / chi phí quảng cáo; fallback GMV / hoa hồng nếu không có QC."""
    if ad_cost > 0:
        return round(gmv / ad_cost, 2)
    if commission > 0:
        return round(gmv / commission, 2)
    return None


def _fetch_ad_by_account(db: Session) -> dict[str, dict[str, float]]:
    """Gom chi phí quảng cáo theo tài khoản TikTok (Creative data)."""
    rows = (
        db.query(
            models.TiktokAdCreative.tiktok_account,
            func.sum(models.TiktokAdCreative.cost).label("cost"),
            func.sum(models.TiktokAdCreative.gross_revenue).label("revenue"),
            func.count(models.TiktokAdCreative.id).label("cnt"),
        )
        .group_by(models.TiktokAdCreative.tiktok_account)
        .all()
    )
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
    """Tìm chi phí QC khớp creator (exact key hoặc substring)."""
    if creator_key in ad_map:
        return ad_map[creator_key]

    best: dict[str, float] = {"ad_cost": 0.0, "ad_revenue": 0.0, "ad_count": 0.0, "account": ""}
    for ad_key, data in ad_map.items():
        if _match_ad_account(creator_key, data.get("account") or ad_key):
            if data["ad_cost"] > best["ad_cost"]:
                best = {**data}
    return best


def get_affiliate_report(
    db: Session,
    sort: str = "gmv",
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Báo cáo affiliate theo creator.
    sort: gmv | views | roi | avg_ad_cost
    """
    # Dữ liệu creator list
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

    # Bổ sung views / gmv từ bảng video (union creator)
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

    merged: dict[str, dict[str, Any]] = {}

    def _ensure(username: Optional[str]) -> dict[str, Any]:
        key = username or ""
        if key not in merged:
            merged[key] = {
                "creator_username": key,
                "gmv": 0.0,
                "views": 0.0,
                "orders": 0.0,
                "commission": 0.0,
                "video_count": 0,
                "followers": 0.0,
            }
        return merged[key]

    for r in creator_rows:
        if not r.creator_username:
            continue
        rec = _ensure(r.creator_username)
        rec["gmv"] = max(rec["gmv"], _safe_float(r.gmv))
        rec["views"] = max(rec["views"], _safe_float(r.views))
        rec["orders"] = max(rec["orders"], _safe_float(r.orders))
        rec["commission"] = max(rec["commission"], _safe_float(r.commission))
        rec["video_count"] = max(rec["video_count"], int(r.video_count or 0))
        rec["followers"] = max(rec["followers"], _safe_float(r.followers))

    for r in video_agg:
        if not r.creator_username:
            continue
        rec = _ensure(r.creator_username)
        if rec["gmv"] == 0:
            rec["gmv"] = _safe_float(r.gmv)
        if rec["views"] == 0:
            rec["views"] = _safe_float(r.views)
        if rec["orders"] == 0:
            rec["orders"] = _safe_float(r.orders)
        if rec["commission"] == 0:
            rec["commission"] = _safe_float(r.commission)
        rec["video_count"] = max(rec["video_count"], int(r.video_count or 0))

    ad_map = _fetch_ad_by_account(db)
    creators: list[dict[str, Any]] = []

    for rec in merged.values():
        if not rec["creator_username"]:
            continue
        ck = _normalize_key(rec["creator_username"])
        ad = _assign_ad_cost(ck, ad_map)
        ad_cost = ad.get("ad_cost", 0.0)
        ad_count = int(ad.get("ad_count", 0) or 0)
        avg_ad = round(ad_cost / ad_count, 0) if ad_count > 0 else None

        gmv = rec["gmv"]
        commission = rec["commission"]
        roi = _calc_roi(gmv, ad_cost, commission)

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
            "roi": roi,
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
    creators = creators[offset : offset + limit]

    total_ad = sum(c["ad_cost_total"] for c in creators)
    ad_with_cost = [c for c in creators if c["avg_ad_cost"]]
    avg_ad_all = round(total_ad / len(ad_with_cost), 0) if ad_with_cost else None

    return {
        "sort": sort,
        "offset": offset,
        "limit": limit,
        "total": total,
        "creators": creators,
        "summary": {
            "total_creators": len(merged),
            "total_gmv": sum(c["gmv"] for c in merged.values()),
            "total_views": sum(c["views"] for c in merged.values()),
            "total_ad_cost": total_ad,
            "avg_ad_cost": avg_ad_all,
        },
    }


def get_creator_videos(
    db: Session,
    creator_username: str,
    sort: str = "gmv",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Chi tiết video affiliate của một creator."""
    rows = (
        db.query(models.TiktokAffiliateVideo)
        .filter(models.TiktokAffiliateVideo.creator_username == creator_username)
        .all()
    )

    videos: list[dict[str, Any]] = []
    for v in rows:
        gmv = _safe_float(v.gmv)
        views = _safe_float(v.shoppable_impressions)
        commission = _safe_float(v.estimated_commission)
        orders = _safe_float(v.linked_orders)
        roi = _calc_roi(gmv, 0, commission)

        videos.append({
            "video_name": v.video_name,
            "posted_date": v.posted_date.isoformat() if v.posted_date else None,
            "gmv": gmv,
            "gmv_video": _safe_float(v.gmv_video),
            "views": views,
            "orders": orders,
            "items_sold": _safe_float(v.items_sold),
            "commission": commission,
            "aov": _safe_float(v.shoppable_aov),
            "ctr": _safe_float(v.linked_ctr),
            "gpm": _safe_float(v.shoppable_gpm),
            "likes": _safe_float(v.shoppable_likes),
            "comments": _safe_float(v.shoppable_comments),
            "gmv_refunded": _safe_float(v.gmv_refunded),
            "roi": roi,
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

    # Creator summary từ creator list
    creator_row = (
        db.query(models.TiktokAffiliateCreator)
        .filter(models.TiktokAffiliateCreator.creator_username == creator_username)
        .first()
    )

    ad_map = _fetch_ad_by_account(db)
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
