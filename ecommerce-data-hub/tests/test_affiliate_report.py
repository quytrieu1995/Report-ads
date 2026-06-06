"""Kiểm thử báo cáo affiliate."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from ingest import ingest_file
from reports.affiliate import get_affiliate_report, get_affiliate_trend, get_creator_videos

SAMPLES = ROOT / "tests" / "samples"
TEST_DB = ROOT / "data" / "test_affiliate_report.db"


def run_test():
    if TEST_DB.exists():
        TEST_DB.unlink()

    engine = create_engine(f"sqlite:///{TEST_DB}")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    files = [
        SAMPLES / "real" / "Creator_List_real.xlsx",
        SAMPLES / "real" / "Creator_Video_List_real.xlsx",
        SAMPLES / "real" / "Creative_data_real.xlsx",
    ]
    for fp in files:
        if fp.exists():
            ingest_file(db, fp.name, fp.read_bytes())

    report = get_affiliate_report(db, sort="gmv", limit=10)
    assert report["creators"], "Expected creators in report"
    top = report["creators"][0]
    assert top["gmv"] > 0
    assert "roi" in top
    assert "avg_ad_cost" in top
    print(f"✓ Affiliate report: {len(report['creators'])} creators, top={top['creator_username']}")

    detail = get_creator_videos(db, "thuanh.review", sort="gmv")
    assert detail["videos"], "Expected videos for thuanh.review"
    assert detail["summary"]["gmv"] > 0
    print(f"✓ Creator detail: {len(detail['videos'])} videos, GMV={detail['summary']['gmv']}")

    by_views = get_affiliate_report(db, sort="views")
    by_roi = get_affiliate_report(db, sort="roi")
    print(f"✓ Sort views OK ({len(by_views['creators'])} rows)")
    print(f"✓ Sort roi OK ({len(by_roi['creators'])} rows)")

    trend = get_affiliate_trend(db)
    assert "daily" in trend and "totals" in trend
    print(f"✓ Affiliate trend: {len(trend['daily'])} days, GMV={trend['totals']['gmv']}")

    db.close()
    print("\n✓ Affiliate report tests passed")


if __name__ == "__main__":
    run_test()
