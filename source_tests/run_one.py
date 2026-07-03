#!/usr/bin/env python3
"""Test a single proxy source: python run_one.py monosans_http"""

from __future__ import annotations

import asyncio
import sys

from common import SOURCES_DIR, SourceConfig, run_source_test, save_report


async def main(source_id: str) -> None:
    path = SOURCES_DIR / f"{source_id}.json"
    if not path.exists():
        print(f"Source not found: {path}")
        print(f"Available: run bootstrap_sources.py first")
        sys.exit(1)

    cfg = SourceConfig.load(path)
    print(f"Testing [{cfg.id}] {cfg.platform} / {cfg.protocol_label}", flush=True)
    print(f"  URL: {cfg.url}", flush=True)

    report = await run_source_test(cfg)
    save_report(cfg, report)

    if not report.fetch_ok:
        print(f"  FAIL fetch: {report.fetch_error}")
    else:
        print(
            f"  fetched={report.total_fetched} tested={report.total_tested} "
            f"working={report.working} rate={report.success_rate}% "
            f"https={report.https_working}"
        )
    print(f"  → results/{cfg.id}.json + .md")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_one.py <source_id>")
        print("Example: python run_one.py proxifly_http")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))