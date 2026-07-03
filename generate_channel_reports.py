#!/usr/bin/env python3
"""Generate per-channel markdown reports from all test result JSON files."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
CHANNELS = RESULTS / "channels"
DEPRECATED = ROOT / "_deprecated" / "results"


def load_json(path: Path) -> dict | list | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def write_md(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.name}")


def fmt_proxy_row(p: dict) -> str:
    proxy = p.get("proxy", "?")
    lat = p.get("latency_ms", "?")
    https = "✓" if p.get("https_ok") else "✗"
    ip = p.get("exit_ip", "?")
    if isinstance(ip, str) and len(ip) > 60:
        ip = ip[:60] + "..."
    return f"| `{proxy}` | {lat} | {https} | {ip} |"


def report_from_test_proxies():
    """Round 1: test_proxies.py — httpbin (deprecated)."""
    data = load_json(DEPRECATED / "report_20260703_104913.json")
    if not data:
        return

    for src in data.get("sources", []):
        name = src["name"]
        safe = name.replace("/", "-").replace(" ", "_").replace("(", "").replace(")", "")
        fname = f"作废-初轮-{safe}.md"

        lines = [
            f"# {name}",
            "",
            "> **状态**: 作废轮次（使用 httpbin.org 验证，该站点封代理导致结果失真）",
            f"> **脚本**: `_deprecated/test_proxies.py`",
            "",
            "## 来源信息",
            "",
            f"- **URL**: `{src.get('url', 'N/A')}`",
            f"- **测试时间**: {data.get('tested_at', 'N/A')}",
            f"- **验证 URL**: `{data.get('test_urls', {}).get('http', 'httpbin')}`",
            "",
            "## 拉取结果",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 拉取成功 | {'是' if src.get('fetch_ok') else '否'} |",
            f"| 列表数量 | {src.get('total_fetched', 0)} |",
            f"| 抽样测试 | {src.get('tested', 0)} |",
            f"| 可用数量 | {src.get('working', 0)} |",
            f"| 成功率 | {src.get('success_rate', 0)}% |",
            f"| HTTPS 可用 | {src.get('https_working', 0)} |",
        ]

        if src.get("fetch_error"):
            lines.extend(["", f"**拉取错误**: {src['fetch_error']}"])

        if src.get("median_latency_ms"):
            lines.extend([
                "",
                "## 延迟统计",
                "",
                f"- 中位: {src['median_latency_ms']}ms",
                f"- 平均: {src.get('avg_latency_ms')}ms",
                f"- 范围: {src.get('min_latency_ms')}-{src.get('max_latency_ms')}ms",
            ])

        working = src.get("working_proxies", [])
        if working:
            lines.extend([
                "",
                "## 可用代理",
                "",
                "| 代理 | 延迟(ms) | HTTPS | 出口IP |",
                "|------|----------|-------|--------|",
            ])
            for p in working:
                lines.append(fmt_proxy_row(p))
        else:
            lines.extend(["", "## 可用代理", "", "无"])

        if src.get("sample_errors"):
            lines.extend(["", "## 常见错误", ""])
            for e in src["sample_errors"]:
                lines.append(f"- `{e}`")

        write_md(CHANNELS / fname, "\n".join(lines))


def report_from_quick_hunt():
    """Round 2: quick_hunt.py results."""
    data = load_json(RESULTS / "quick_working.json")
    if not data:
        return

    meta = data.get("meta", {})
    by_source: dict[str, list] = defaultdict(list)

    for p in data.get("proxies", []):
        for src in p.get("sources", [p.get("source", "unknown")]):
            by_source[src].append(p)

    # Per-source channel reports
    for src_name, proxies in by_source.items():
        safe = src_name.replace("/", "-").replace(" ", "_").replace("(", "").replace(")", "")
        src_meta = next((s for s in meta.get("sources", []) if s["name"] == src_name), {})

        lines = [
            f"# {src_name}",
            "",
            "> **状态**: 有效（使用 icanhazip.com 验证，两轮筛选）",
            "> **脚本**: `quick_hunt.py`",
            "",
            "## 来源信息",
            "",
            f"- **URL**: `{src_meta.get('url', 'N/A')}`",
            f"- **测试时间**: {meta.get('finished_at', 'N/A')}",
            f"- **拉取数量**: {src_meta.get('fetched', '?')}",
            f"- **本渠道验证通过**: {len(proxies)}",
            "",
            "## 可用代理",
            "",
            "| 代理 | 延迟(ms) | HTTPS | 出口IP |",
            "|------|----------|-------|--------|",
        ]
        for p in sorted(proxies, key=lambda x: x.get("latency_ms") or 9999):
            lines.append(fmt_proxy_row(p))

        write_md(CHANNELS / f"quick_hunt-{safe}.md", "\n".join(lines))

    # Summary for quick_hunt
    lines = [
        "# 快速搜寻总览 (quick_hunt)",
        "",
        f"- **时间**: {meta.get('started_at')} → {meta.get('finished_at')}",
        f"- **候选数**: {meta.get('unique_candidates', '?')}",
        f"- **一轮通过**: {meta.get('round1_survivors', '?')}",
        f"- **二轮通过**: {meta.get('round2_survivors', '?')}",
        f"- **耗时**: {meta.get('duration_s')}s",
        "",
        "## 各渠道拉取",
        "",
        "| 渠道 | 拉取数 | 验证通过 |",
        "|------|--------|----------|",
    ]
    for s in meta.get("sources", []):
        passed = len(by_source.get(s["name"], []))
        lines.append(f"| {s['name']} | {s.get('fetched', 0)} | {passed} |")
    lines.extend(["", "## 分渠道报告", ""])
    for src_name in sorted(by_source):
        safe = src_name.replace("/", "-").replace(" ", "_").replace("(", "").replace(")", "")
        lines.append(f"- [`quick_hunt-{safe}.md`](./quick_hunt-{safe}.md)")

    write_md(CHANNELS / "quick_hunt-总览.md", "\n".join(lines))


def report_from_geonode_hunt():
    """Round 3: geonode_hunt.py — merged results."""
    data = load_json(RESULTS / "ALL_WORKING.json")
    if not data:
        return

    by_source: dict[str, list] = defaultdict(list)
    for p in data.get("proxies", []):
        sources = p.get("sources") or [p.get("source", "unknown")]
        for src in sources:
            by_source[src].append(p)

    for src_name, proxies in by_source.items():
        safe = src_name.replace("/", "-").replace(" ", "_").replace("(", "").replace(")", "")

        https_count = sum(1 for p in proxies if p.get("https_ok"))
        lines = [
            f"# {src_name}",
            "",
            "> **状态**: 有效（深度搜寻合并结果）",
            "> **脚本**: `geonode_hunt.py`",
            "",
            f"- **搜寻时间**: {data.get('hunted_at', 'N/A')}",
            f"- **本渠道可用**: {len(proxies)}",
            f"- **其中 HTTPS**: {https_count}",
            "",
            "## 可用代理",
            "",
            "| 代理 | 延迟(ms) | HTTPS | 出口IP |",
            "|------|----------|-------|--------|",
        ]
        for p in sorted(proxies, key=lambda x: x.get("latency_ms") or 9999):
            lines.append(fmt_proxy_row(p))

        write_md(CHANNELS / f"geonode_hunt-{safe}.md", "\n".join(lines))

    lines = [
        "# 深度搜寻总览 (geonode_hunt)",
        "",
        f"- **时间**: {data.get('hunted_at')}",
        f"- **总可用**: {data.get('total', 0)}",
        f"- **优质 (HTTPS<3s)**: {data.get('premium_count', 0)}",
        f"- **本轮新发现**: {data.get('new_found', 0)}",
        "",
        "## 各渠道贡献",
        "",
        "| 渠道 | 可用数 | HTTPS数 |",
        "|------|--------|---------|",
    ]
    for src_name in sorted(by_source, key=lambda x: -len(by_source[x])):
        proxies = by_source[src_name]
        https_n = sum(1 for p in proxies if p.get("https_ok"))
        lines.append(f"| {src_name} | {len(proxies)} | {https_n} |")

    lines.extend(["", "## 分渠道报告", ""])
    for src_name in sorted(by_source):
        safe = src_name.replace("/", "-").replace(" ", "_").replace("(", "").replace(")", "")
        lines.append(f"- [`geonode_hunt-{safe}.md`](./geonode_hunt-{safe}.md)")

    write_md(CHANNELS / "geonode_hunt-总览.md", "\n".join(lines))


def report_premium_verified():
    """Premium proxy real-world verification."""
    data = load_json(RESULTS / "PREMIUM_VERIFIED.json")
    if not data:
        return

    lines = [
        "# 优质代理真实站点验证",
        "",
        "> **脚本**: 内联验证脚本（icanhazip / Google / Moltbook API）",
        f"> **验证数量**: {len(data)}",
        "",
        "## 验证结果",
        "",
        "| 代理 | 延迟 | HTTPS | Google | Moltbook | 出口IP | 状态 |",
        "|------|------|-------|--------|----------|--------|------|",
    ]

    for r in sorted(data, key=lambda x: x.get("latency") or 99999):
        t = r.get("targets", {})
        if r.get("error") or not t:
            status = "失效"
            lat = "—"
            https = google = moltbook = "—"
        else:
            status = "可用"
            lat = f"{r.get('latency')}ms"
            https = t.get("https_ip", "?")
            google = t.get("google", "?")
            moltbook = t.get("moltbook", "?")

        ip = r.get("ip", "?")
        if isinstance(ip, str) and len(ip) > 30:
            ip = ip[:30]
        lines.append(
            f"| `{r['proxy']}` | {lat} | {https} | {google} | {moltbook} | {ip} | {status} |"
        )

    # Best for crawling subset
    best = [
        r for r in data
        if r.get("targets", {}).get("moltbook") == 200
        and r.get("targets", {}).get("https_ip") == 200
        and not r.get("error")
    ]
    lines.extend([
        "",
        f"## 可爬 Moltbook（{len(best)} 个）",
        "",
    ])
    for r in sorted(best, key=lambda x: x.get("latency") or 99999):
        lines.append(f"- `{r['proxy']}` — {r.get('latency')}ms, ip={r.get('ip')}")

    write_md(CHANNELS / "优质代理-真实站点验证.md", "\n".join(lines))


def report_overview():
    """Master overview linking all channel reports."""
    channel_files = sorted(CHANNELS.glob("*.md"))
    deprecated_files = sorted((ROOT / "_deprecated").rglob("*"))
    deprecated_scripts = [f for f in deprecated_files if f.suffix == ".py"]

    lines = [
        "# 代理测试 — 渠道结果总览",
        "",
        "## 目录结构",
        "",
        "```",
        "proxy-hunter/",
        "├── geonode_hunt.py      # 推荐：深度搜寻",
        "├── quick_hunt.py        # 快速搜寻",
        "├── final_verify.py      # 真实站点验证",
        "├── requirements.txt",
        "├── _deprecated/         # 作废脚本与早期结果",
        "└── results/",
        "    ├── channels/        # 各渠道 .md 报告（本目录）",
        "    ├── ALL_WORKING.json # 全部可用代理",
        "    ├── BEST_FOR_CRAWLING.txt",
        "    └── FINAL_REPORT.md  # 最终总结",
        "```",
        "",
        "## 测试轮次",
        "",
        "| 轮次 | 脚本 | 状态 | 验证方式 | 说明 |",
        "|------|------|------|----------|------|",
        "| 1 | `test_proxies.py` | **作废** | httpbin.org | 结果失真，已归档 |",
        "| 2 | `quick_hunt.py` | 有效 | icanhazip.com | 22 个通过二轮验证 |",
        "| 3 | `geonode_hunt.py` | 有效 | icanhazip.com | 77 个可用，11 优质 |",
        "| 4 | 优质代理实测 | 有效 | 真实站点 | 8 个可爬 Moltbook |",
        "| — | `proxy_hunter.py` | **作废** | icanhazip | 全量 11594 候选，运行中断 |",
        "",
        "## 作废文件夹 (_deprecated)",
        "",
        "| 文件 | 原因 |",
        "|------|------|",
        "| `test_proxies.py` | 使用 httpbin 导致成功率虚低 |",
        "| `proxy_hunter.py` | 全量扫描过慢，中途终止，部分源有 bug |",
        "| `run.sh` | 仅用于 test_proxies.py |",
        "| `results/report_20260703_*` | 初轮作废测试结果 |",
        "| `results/final_verified.json` | 被 ALL_WORKING.json 取代 |",
        "",
        "## 渠道报告索引",
        "",
    ]

    groups = {
        "作废-初轮": [],
        "quick_hunt": [],
        "geonode_hunt": [],
        "其他": [],
    }
    for f in channel_files:
        if f.name == "00-总览.md":
            continue
        name = f.name
        if name.startswith("作废"):
            groups["作废-初轮"].append(name)
        elif name.startswith("quick_hunt"):
            groups["quick_hunt"].append(name)
        elif name.startswith("geonode_hunt"):
            groups["geonode_hunt"].append(name)
        else:
            groups["其他"].append(name)

    labels = {
        "作废-初轮": "第一轮（作废，httpbin）",
        "quick_hunt": "快速搜寻 (quick_hunt.py)",
        "geonode_hunt": "深度搜寻 (geonode_hunt.py)",
        "其他": "验证与其他",
    }
    for key, files in groups.items():
        if files:
            lines.append(f"### {labels[key]}")
            lines.append("")
            for fn in sorted(files):
                lines.append(f"- [{fn}](./{fn})")
            lines.append("")

    lines.extend([
        "## 最终可用数据文件",
        "",
        "| 文件 | 内容 |",
        "|------|------|",
        "| `../BEST_FOR_CRAWLING.txt` | 8 个可爬 Moltbook 代理 |",
        "| `../ALL_PREMIUM.txt` | 11 个 HTTPS 优质代理 |",
        "| `../ALL_WORKING.json` | 77 个全部可用代理 |",
        "| `../FINAL_REPORT.md` | 最终总结报告 |",
    ])

    write_md(CHANNELS / "00-总览.md", "\n".join(lines))


def main():
    CHANNELS.mkdir(parents=True, exist_ok=True)
    print("Generating channel reports...")
    report_from_test_proxies()
    report_from_quick_hunt()
    report_from_geonode_hunt()
    report_premium_verified()
    report_overview()
    print("Done.")


if __name__ == "__main__":
    main()