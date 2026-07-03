#!/usr/bin/env python3
"""Run all source tests sequentially (one platform at a time, no aggregation)."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from common import RESULTS_DIR, SOURCES_DIR, SourceConfig, run_source_test, save_report

RANKING_PATH = RESULTS_DIR / "00_RANKING.md"


async def main() -> None:
    configs = sorted(
        (SourceConfig.load(p) for p in SOURCES_DIR.glob("*.json")),
        key=lambda c: c.id,
    )
    if not configs:
        print("No sources found. Run: python bootstrap_sources.py")
        return

    print(f"=== Source Tests: {len(configs)} platforms (isolated) ===\n", flush=True)
    started = time.time()
    summaries = []

    for i, cfg in enumerate(configs, 1):
        print(f"[{i}/{len(configs)}] {cfg.id} ...", flush=True)
        report = await run_source_test(cfg)
        save_report(cfg, report)
        summaries.append({
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
            "error": report.fetch_error,
        })
        status = f"{report.working}/{report.total_tested} ({report.success_rate}%)" if report.fetch_ok else f"FAIL: {report.fetch_error}"
        print(f"       → {status}\n", flush=True)

    elapsed = round(time.time() - started, 1)
    ok = [s for s in summaries if s["fetch_ok"] and s["tested"] > 0]
    ok.sort(key=lambda x: (-x["success_rate"], -(x["working"]), x["median_latency_ms"] or 9999))

    lines = [
        "# 各平台代理可用度排名（独立测试）",
        "",
        f"- **测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"- **平台数量**: {len(configs)}",
        f"- **每平台抽样**: 最多 50 个",
        f"- **验证端点**: icanhazip.com",
        f"- **总耗时**: {elapsed}s",
        "",
        "## 排名（按成功率 → 可用数）",
        "",
        "| 排名 | Source ID | 平台 | 协议 | 拉取 | 测试 | 可用 | 成功率 | HTTPS | 中位延迟 |",
        "|------|-----------|------|------|------|------|------|--------|-------|----------|",
    ]
    for rank, s in enumerate(ok, 1):
        med = s["median_latency_ms"] or "—"
        lines.append(
            f"| {rank} | `{s['id']}` | {s['platform']} | {s['protocol']} | "
            f"{s['fetched']} | {s['tested']} | {s['working']} | **{s['success_rate']}%** | "
            f"{s['https_working']} | {med} |"
        )

    failed = [s for s in summaries if not s["fetch_ok"]]
    if failed:
        lines.extend(["", "## 拉取失败", ""])
        for s in failed:
            lines.append(f"- `{s['id']}`: {s['error']}")

    lines.extend([
        "",
        "## 分平台报告",
        "",
        "每个平台独立结果见 `results/{source_id}.md`",
        "",
    ])
    for cfg in configs:
        lines.append(f"- [{cfg.id}](./{cfg.id}.md) — {cfg.platform} / {cfg.protocol_label}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RANKING_PATH.write_text("\n".join(lines), encoding="utf-8")
    (RESULTS_DIR / "00_RANKING.json").write_text(
        json.dumps({"elapsed_s": elapsed, "summaries": summaries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=" * 50)
    print(f"Done in {elapsed}s. Ranking: results/00_RANKING.md")
    if ok:
        print("\nTop 5:")
        for s in ok[:5]:
            print(f"  {s['id']}: {s['success_rate']}% ({s['working']}/{s['tested']})")


if __name__ == "__main__":
    asyncio.run(main())