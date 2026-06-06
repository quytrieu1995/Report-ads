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


def _insert_rows(db: Session, model_cls: type, batch_id: int, rows: list[dict]) -> int:
    """Ghi danh sách dict vào bảng fact."""
    count = 0
    for row in rows:
        obj = model_cls(batch_id=batch_id, **row)
        db.add(obj)
        count += 1
    return count


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
            total_rows += _insert_rows(db, models.ShopeeShopDaily, batch.id, daily_rows)
            total_rows += _insert_rows(db, models.ShopeeProductStat, batch.id, product_rows)
        else:
            assert isinstance(parsed, list)
            model_classes = MODEL_MAP[source_type]
            total_rows = _insert_rows(db, model_classes[0], batch.id, parsed)

        batch.row_count = total_rows
        batch.status = "success"
        batch.message = f"Đã nạp {total_rows} dòng"
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
