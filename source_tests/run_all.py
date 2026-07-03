#!/usr/bin/env python3
"""Run all source tests with parallel workers and optional resume."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from common import (
    RESULTS_DIR,
    SOURCES_DIR,
    SourceConfig,
    TestSettings,
    result_is_fresh,
    run_source_test,
    save_report,
)

RANKING_PATH = RESULTS_DIR / "00_RANKING.md"


def build_ranking(configs: list[SourceConfig], summaries: list[dict], elapsed: float, settings: TestSettings) -> None:
    ok = [s for s in summaries if s.get("fetch_ok") and s.get("tested", 0) > 0]
    ok.sort(key=lambda x: (-x["success_rate"], -(x["working"]), x.get("median_latency_ms") or 9999))

    lines = [
        "# 各平台代理可用度排名（独立测试）",
        "",
        f"- **测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"- **平台数量**: {len(configs)}",
        f"- **每平台抽样**: 最多 {settings.max_test} 个",
        f"- **并发**: {settings.concurrency} | **超时**: {settings.timeout}s",
        f"- **验证端点**: icanhazip.com",
        f"- **总耗时**: {elapsed}s",
        "",
        "## 排名（按成功率 → 可用数）",
        "",
        "| 排名 | Source ID | 平台 | 协议 | 拉取 | 测试 | 可用 | 成功率 | HTTPS | 验证耗时 | 中位延迟 |",
        "|------|-----------|------|------|------|------|------|--------|-------|----------|----------|",
    ]
    for rank, s in enumerate(ok, 1):
        med = s.get("median_latency_ms") or "—"
        vms = s.get("validate_ms") or "—"
        lines.append(
            f"| {rank} | `{s['id']}` | {s['platform']} | {s['protocol']} | "
            f"{s['fetched']} | {s['tested']} | {s['working']} | **{s['success_rate']}%** | "
            f"{s['https_working']} | {vms}ms | {med} |"
        )

    skipped = [s for s in summaries if s.get("skipped")]
    failed = [s for s in summaries if not s.get("fetch_ok") and not s.get("skipped")]
    if skipped:
        lines.extend(["", "## 跳过（已有新鲜结果）", ""])
        for s in skipped:
            lines.append(f"- `{s['id']}`")
    if failed:
        lines.extend(["", "## 拉取失败", ""])
        for s in failed:
            lines.append(f"- `{s['id']}`: {s.get('error')}")

    lines.extend(["", "## 分平台报告", "", "每个平台独立结果见 `results/{source_id}.md`", ""])
    for cfg in configs:
        lines.append(f"- [{cfg.id}](./{cfg.id}.md) — {cfg.platform} / {cfg.protocol_label}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RANKING_PATH.write_text("\n".join(lines), encoding="utf-8")
    (RESULTS_DIR / "00_RANKING.json").write_text(
        json.dumps({"elapsed_s": elapsed, "summaries": summaries, "settings": settings.__dict__}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_cached_summary(cfg: SourceConfig) -> dict:
    data = json.loads((RESULTS_DIR / f"{cfg.id}.json").read_text(encoding="utf-8"))
    return {
        "id": cfg.id,
        "platform": cfg.platform,
        "protocol": cfg.protocol_label,
        "fetch_ok": data.get("fetch_ok", True),
        "fetched": data.get("total_fetched", 0),
        "tested": data.get("total_tested", 0),
        "working": data.get("working", 0),
        "success_rate": data.get("success_rate", 0),
        "https_working": data.get("https_working", 0),
        "median_latency_ms": data.get("median_latency_ms"),
        "validate_ms": data.get("validate_ms"),
        "skipped": True,
    }


async def test_one(
    cfg: SourceConfig,
    settings: TestSettings,
    index: int,
    total: int,
    use_cache: bool,
    sem: asyncio.Semaphore,
) -> dict:
    async with sem:
        t0 = time.perf_counter()
        print(f"[{index}/{total}] {cfg.id} ...", flush=True)

        def progress(done: int, n: int) -> None:
            if done == n or done % 20 == 0:
                print(f"       {cfg.id}: {done}/{n}", end="\r", flush=True)

        report = await run_source_test(cfg, settings=settings, use_cache=use_cache, on_progress=progress)
        save_report(cfg, report, settings)
        elapsed = round(time.perf_counter() - t0, 1)

        summary = {
            "id": cfg.id,
            "platform": cfg.platform,
            "protocol": cfg.protocol_label,
            "fetch_ok": report.fetch_ok,
            "fetched": report.total_fetched,
            "tested": report.total_tested,
            "working": report.working,
            "success_rate": report.success_rate,
            "https_working": report.https_working,
            "median_latency_ms": report.median_latency_ms,
            "validate_ms": report.validate_ms,
            "error": report.fetch_error,
            "elapsed_s": elapsed,
        }
        if report.fetch_ok:
            print(
                f"       → {report.working}/{report.total_tested} ({report.success_rate}%) "
                f"validate={report.validate_ms}ms total={elapsed}s    ",
                flush=True,
            )
        else:
            print(f"       → FAIL: {report.fetch_error} ({elapsed}s)", flush=True)
        return summary


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run isolated proxy source tests")
    parser.add_argument("--workers", type=int, default=4, help="parallel platforms (default 4)")
    parser.add_argument("--concurrency", type=int, default=40, help="proxy validate concurrency per platform")
    parser.add_argument("--timeout", type=float, default=6.0, help="per-request timeout seconds")
    parser.add_argument("--max-test", type=int, default=50, help="max proxies sampled per platform")
    parser.add_argument("--skip-existing", action="store_true", help="skip if result < 1h old")
    parser.add_argument("--no-cache", action="store_true", help="refetch lists, ignore .cache")
    parser.add_argument("--no-https", action="store_true", help="skip HTTPS check (faster)")
    parser.add_argument("--only", type=str, default="", help="comma-separated source ids")
    args = parser.parse_args()

    settings = TestSettings(
        timeout=args.timeout,
        concurrency=args.concurrency,
        max_test=args.max_test,
        check_https=not args.no_https,
    )

    configs = sorted(
        (SourceConfig.load(p) for p in SOURCES_DIR.glob("*.json")),
        key=lambda c: c.id,
    )
    if args.only:
        allow = {x.strip() for x in args.only.split(",") if x.strip()}
        configs = [c for c in configs if c.id in allow]

    if not configs:
        print("No sources found. Run: python bootstrap_sources.py")
        return

    print(
        f"=== Source Tests: {len(configs)} platforms | workers={args.workers} "
        f"concurrency={settings.concurrency} timeout={settings.timeout}s ===\n",
        flush=True,
    )

    started = time.time()
    summaries: list[dict] = []
    to_run: list[tuple[int, SourceConfig]] = []

    for i, cfg in enumerate(configs, 1):
        if args.skip_existing and result_is_fresh(cfg.id):
            print(f"[{i}/{len(configs)}] {cfg.id} ... skipped (fresh cache)", flush=True)
            summaries.append(load_cached_summary(cfg))
        else:
            to_run.append((i, cfg))

    sem = asyncio.Semaphore(args.workers)
    if to_run:
        results = await asyncio.gather(
            *[
                test_one(cfg, settings, idx, len(configs), not args.no_cache, sem)
                for idx, cfg in to_run
            ]
        )
        summaries.extend(results)

    summaries.sort(key=lambda s: s["id"])
    elapsed = round(time.time() - started, 1)
    build_ranking(configs, summaries, elapsed, settings)

    ok = [s for s in summaries if s.get("fetch_ok") and s.get("tested", 0) > 0]
    ok.sort(key=lambda x: (-x["success_rate"], -(x["working"])))

    print("\n" + "=" * 50)
    print(f"Done in {elapsed}s. Ranking: results/00_RANKING.md")
    if ok:
        print("\nTop 5:")
        for s in ok[:5]:
            print(f"  {s['id']}: {s['success_rate']}% ({s['working']}/{s['tested']})")


if __name__ == "__main__":
    asyncio.run(main())