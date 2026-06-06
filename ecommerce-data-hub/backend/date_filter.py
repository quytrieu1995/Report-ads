"""Helper lọc theo khoảng thời gian — tuần, tháng, tuỳ chọn."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Query


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def resolve_date_range(
    preset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> tuple[Optional[date], Optional[date]]:
    """
    Trả (date_from, date_to) inclusive.
    preset: week | month | custom | None/all → không lọc
    """
    today = date.today()

    if preset == "week":
        # Tuần hiện tại (Thứ 2 → hôm nay)
        start = today - timedelta(days=today.weekday())
        return start, today

    if preset == "month":
        start = today.replace(day=1)
        return start, today

    if preset == "custom" or date_from or date_to:
        start = parse_date(date_from)
        end = parse_date(date_to) or today
        if start and end and start > end:
            start, end = end, start
        return start, end

    return None, None


def apply_date_filter(query: Query, column, date_from: Optional[date], date_to: Optional[date]) -> Query:
    """Thêm điều kiện ngày vào query SQLAlchemy."""
    if date_from is not None:
        query = query.filter(column >= date_from)
    if date_to is not None:
        query = query.filter(column <= date_to)
    return query


def range_to_dict(date_from: Optional[date], date_to: Optional[date]) -> dict:
    return {
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "active": date_from is not None or date_to is not None,
    }
