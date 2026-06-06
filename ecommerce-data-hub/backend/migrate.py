"""Tự động thêm cột mới vào DB SQLite cũ (không cần xóa datahub.db)."""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _column_ddl(col, dialect) -> str:
    """Sinh kiểu cột cho ALTER TABLE SQLite."""
    return col.type.compile(dialect=dialect)


def migrate_schema(engine: Engine, metadata) -> list[str]:
    """
    So sánh schema ORM với DB thực tế, ADD COLUMN nếu thiếu.
    Trả về danh sách cột đã thêm.
    """
    if not str(engine.url).startswith("sqlite"):
        return []

    inspector = inspect(engine)
    added: list[str] = []
    dialect = engine.dialect

    with engine.begin() as conn:
        for table_name, table in metadata.tables.items():
            if not inspector.has_table(table_name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table_name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                col_type = _column_ddl(col, dialect)
                sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}'
                conn.execute(text(sql))
                added.append(f"{table_name}.{col.name}")

    return added


def init_db(engine: Engine, metadata) -> None:
    """Tạo bảng mới + migrate cột thiếu."""
    metadata.create_all(bind=engine)
    added = migrate_schema(engine, metadata)
    if added:
        print(f"[DB migrate] Đã thêm {len(added)} cột: {', '.join(added)}")
