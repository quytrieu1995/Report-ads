"""Nạp file vào DB — chống trùng hash, lineage theo batch."""
from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.orm import Session

import models
from parsers import (
    PLATFORM_MAP,
    detect_source_type,
    extract_period_from_filename,
    parse_file,
)

# Map source_type → model class(es)
MODEL_MAP: dict[str, list[type]] = {
    "tiktok_order": [models.TiktokOrder],
    "tiktok_ad_creative": [models.TiktokAdCreative],
    "tiktok_affiliate_creator": [models.TiktokAffiliateCreator],
    "tiktok_affiliate_video": [models.TiktokAffiliateVideo],
    "shopee_shop": [models.ShopeeShopDaily, models.ShopeeProductStat],
}


def _file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _insert_rows(db: Session, model_cls: type, batch_id: int, rows: list[dict]) -> tuple[int, dict]:
    """Ghi danh sách dict vào bảng fact — bỏ key nội bộ (_fx_rate...)."""
    count = 0
    meta: dict = {"usd_converted": 0, "fx_rate": None, "fx_source": None}
    for row in rows:
        if row.get("_fx_from") == "USD":
            meta["usd_converted"] += 1
            meta["fx_rate"] = row.get("_fx_rate")
            meta["fx_source"] = row.get("_fx_source")
        clean = {k: v for k, v in row.items() if not k.startswith("_")}
        obj = model_cls(batch_id=batch_id, **clean)
        db.add(obj)
        count += 1
    return count, meta


def ingest_file(db: Session, filename: str, content: bytes) -> dict[str, Any]:
    """
    Nạp một file:
    - Tính hash, chặn trùng batch success
    - Detect → parse → ghi DB
    - Lỗi → rollback, batch failed
    """
    fhash = _file_hash(content)

    existing = (
        db.query(models.UploadBatch)
        .filter(models.UploadBatch.file_hash == fhash, models.UploadBatch.status == "success")
        .first()
    )
    if existing:
        return {
            "filename": filename,
            "status": "duplicate",
            "batch_id": existing.id,
            "message": f"File đã được nạp trước đó (batch #{existing.id})",
        }

    source_type = detect_source_type(filename, content)
    platform = PLATFORM_MAP.get(source_type, "unknown")
    period_start, period_end = extract_period_from_filename(filename)

    batch = models.UploadBatch(
        filename=filename,
        source_type=source_type,
        platform=platform,
        period_start=period_start,
        period_end=period_end,
        status="pending",
        file_hash=fhash,
        row_count=0,
    )
    db.add(batch)
    db.flush()

    try:
        parsed = parse_file(source_type, content)
        total_rows = 0

        if source_type == "shopee_shop":
            assert isinstance(parsed, dict)
            daily_rows = parsed.get("daily", [])
            product_rows = parsed.get("product", [])
            n1, _ = _insert_rows(db, models.ShopeeShopDaily, batch.id, daily_rows)
            n2, _ = _insert_rows(db, models.ShopeeProductStat, batch.id, product_rows)
            total_rows = n1 + n2
            fx_meta = {}
        else:
            assert isinstance(parsed, list)
            model_classes = MODEL_MAP[source_type]
            total_rows, fx_meta = _insert_rows(db, model_classes[0], batch.id, parsed)

        batch.row_count = total_rows
        batch.status = "success"
        msg = f"Đã nạp {total_rows} dòng"
        if fx_meta.get("usd_converted"):
            rate = fx_meta.get("fx_rate")
            msg += f" · Quy đổi {fx_meta['usd_converted']} dòng USD→VND (1 USD = {rate:,.0f} VND)"
        batch.message = msg
        db.commit()

        return {
            "filename": filename,
            "status": "success",
            "batch_id": batch.id,
            "source_type": source_type,
            "platform": platform,
            "row_count": total_rows,
            "message": batch.message,
        }

    except Exception as exc:
        db.rollback()
        # Tạo lại batch failed (session đã rollback)
        failed = models.UploadBatch(
            filename=filename,
            source_type=source_type,
            platform=platform,
            period_start=period_start,
            period_end=period_end,
            status="failed",
            file_hash=fhash,
            row_count=0,
            message=str(exc),
        )
        db.add(failed)
        db.commit()
        raise


def delete_batch(db: Session, batch_id: int) -> bool:
    """Xoá batch — CASCADE xoá fact rows."""
    batch = db.query(models.UploadBatch).filter(models.UploadBatch.id == batch_id).first()
    if not batch:
        return False
    db.delete(batch)
    db.commit()
    return True
