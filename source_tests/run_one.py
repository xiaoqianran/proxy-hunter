#!/usr/bin/env python3
"""Test a single proxy source: python run_one.py proxifly_http [--turbo]"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from common import SOURCES_DIR, SourceConfig, TestSettings, install_uvloop, run_source_test, save_report_async


async def async_main(source_id: str, settings: TestSettings, use_cache: bool) -> None:
    path = SOURCES_DIR / f"{source_id}.json"
    if not path.exists():
        print(f"Source not found: {path}")
        sys.exit(1)

    cfg = SourceConfig.load(path)
    print(f"Testing [{cfg.id}] {cfg.platform} / {cfg.protocol_label}", flush=True)
    print(f"  URL: {cfg.url}", flush=True)

    t0 = time.perf_counter()

    def progress(done: int, total: int) -> None:
        print(f"  progress: {done}/{total}", end="\r", flush=True)

    report = await run_source_test(cfg, settings=settings, use_cache=use_cache, on_progress=progress)
    await save_report_async(cfg, report, settings)
    elapsed = round(time.perf_counter() - t0, 1)

    print(" " * 40, end="\r")
    if not report.fetch_ok:
        print(f"  FAIL fetch: {report.fetch_error} ({elapsed}s)")
    else:
        print(
            f"  fetched={report.total_fetched} tested={report.total_tested} "
            f"working={report.working} rate={report.success_rate}% "
            f"https={report.https_working} validate={report.validate_ms}ms total={elapsed}s"
        )
    print(f"  → results/{cfg.id}.json + .md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_id", help="e.g. proxifly_http")
    parser.add_argument("--concurrency", type=int, default=80)
    parser.add_argument("--timeout", type=float, default=4.0)
    parser.add_argument("--max-test", type=int, default=None)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--no-https", action="store_true")
    parser.add_argument("--turbo", action="store_true", help="concurrency=120 timeout=3.5")
    args = parser.parse_args()

    path = SOURCES_DIR / f"{args.source_id}.json"
    cfg = SourceConfig.load(path) if path.exists() else None
    concurrency = 120 if args.turbo else args.concurrency
    timeout = 3.5 if args.turbo else args.timeout
    settings = TestSettings(
        concurrency=concurrency,
        timeout=timeout,
        connect_timeout=min(2.0, timeout * 0.5),
        max_test=args.max_test or (cfg.max_test if cfg else 50),
        check_https=not args.no_https,
    )
    install_uvloop()
    asyncio.run(async_main(args.source_id, settings, use_cache=not args.no_cache))


if __name__ == "__main__":
    main()