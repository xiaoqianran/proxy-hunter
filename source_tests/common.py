"""Shared fetch + validate logic for per-source proxy tests."""

from __future__ import annotations

import asyncio
import json
import random
import re
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp_socks import ProxyConnector

ROOT = Path(__file__).parent
SOURCES_DIR = ROOT / "sources"
RESULTS_DIR = ROOT / "results"

TEST_HTTP = "http://icanhazip.com"
TEST_HTTPS = "https://icanhazip.com"
DEFAULT_TIMEOUT = 8
DEFAULT_CONCURRENCY = 25
DEFAULT_MAX_TEST = 50  # per-source cap for fair comparison

IP_PORT = re.compile(r"^\d+\.\d+\.\d+\.\d+:\d+$")


@dataclass
class SourceConfig:
    id: str
    platform: str
    protocol_label: str
    url: str
    scheme: str  # http | socks4 | socks5
    format: str = "txt"  # txt | json
    update_frequency: str = ""
    notes: str = ""
    max_test: int = DEFAULT_MAX_TEST

    @classmethod
    def load(cls, path: Path) -> "SourceConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)


@dataclass
class ProxyHit:
    proxy: str
    latency_ms: float
    https_ok: bool
    exit_ip: str


@dataclass
class SourceReport:
    source_id: str
    platform: str
    protocol_label: str
    url: str
    tested_at: str
    fetch_ok: bool = False
    fetch_error: str | None = None
    fetch_ms: float | None = None
    total_fetched: int = 0
    total_tested: int = 0
    working: int = 0
    https_working: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float | None = None
    median_latency_ms: float | None = None
    working_proxies: list[dict[str, Any]] = field(default_factory=list)
    sample_errors: list[str] = field(default_factory=list)


def parse_body(text: str, scheme: str, fmt: str) -> list[str]:
    proxies: list[str] = []
    if fmt == "json":
        data = json.loads(text)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    proxies.append(item if "://" in item else f"{scheme}://{item}")
                elif isinstance(item, dict):
                    p = item.get("proxy") or item.get("ip")
                    if p and "://" in str(p):
                        proxies.append(str(p))
                    elif item.get("ip") and item.get("port"):
                        proxies.append(f"{scheme}://{item['ip']}:{item['port']}")
        return proxies

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "://" in line:
            proxies.append(line)
        elif IP_PORT.match(line):
            proxies.append(f"{scheme}://{line}")
    return proxies


async def fetch_list(cfg: SourceConfig) -> tuple[list[str], str | None, float]:
    start = time.perf_counter()
    try:
        async with aiohttp.ClientSession(
            headers={"User-Agent": "ProxyHunter-SourceTest/1.0"}
        ) as session:
            async with session.get(
                cfg.url, timeout=aiohttp.ClientTimeout(total=25)
            ) as resp:
                ms = (time.perf_counter() - start) * 1000
                if resp.status != 200:
                    return [], f"HTTP {resp.status}", ms
                text = await resp.text()
                proxies = parse_body(text, cfg.scheme, cfg.format)
                return proxies, None, ms
    except Exception as e:
        return [], str(e)[:200], (time.perf_counter() - start) * 1000


async def test_proxy(proxy: str, timeout: int, sem: asyncio.Semaphore) -> ProxyHit | None:
    async with sem:
        is_socks = proxy.startswith("socks")
        try:
            if is_socks:
                connector = ProxyConnector.from_url(proxy)
                ctx = aiohttp.ClientSession(connector=connector)
            else:
                ctx = aiohttp.ClientSession()

            async with ctx as session:
                t0 = time.perf_counter()
                async with session.get(
                    TEST_HTTP,
                    proxy=None if is_socks else proxy,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        return None
                    ip = (await resp.text()).strip()[:60]
                    lat = round((time.perf_counter() - t0) * 1000, 1)

                https_ok = False
                try:
                    async with session.get(
                        TEST_HTTPS,
                        proxy=None if is_socks else proxy,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                    ) as resp2:
                        https_ok = resp2.status == 200
                except Exception:
                    pass

                return ProxyHit(proxy, lat, https_ok, ip)
        except Exception:
            return None


async def run_source_test(
    cfg: SourceConfig,
    timeout: int = DEFAULT_TIMEOUT,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> SourceReport:
    report = SourceReport(
        source_id=cfg.id,
        platform=cfg.platform,
        protocol_label=cfg.protocol_label,
        url=cfg.url,
        tested_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    )

    proxies, err, fetch_ms = await fetch_list(cfg)
    report.fetch_ms = round(fetch_ms, 1)
    report.total_fetched = len(proxies)

    if err:
        report.fetch_error = err
        return report

    report.fetch_ok = True
    if not proxies:
        report.fetch_error = "Empty proxy list"
        return report

    # Sample for fair cross-platform comparison
    if len(proxies) > cfg.max_test:
        sample = random.sample(proxies, cfg.max_test)
    else:
        sample = proxies

    report.total_tested = len(sample)
    sem = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*[test_proxy(p, timeout, sem) for p in sample])
    hits = [r for r in results if r]

    report.working = len(hits)
    report.https_working = sum(1 for h in hits if h.https_ok)
    report.success_rate = round(report.working / report.total_tested * 100, 1) if report.total_tested else 0

    latencies = [h.latency_ms for h in hits]
    if latencies:
        report.avg_latency_ms = round(statistics.mean(latencies), 1)
        report.median_latency_ms = round(statistics.median(latencies), 1)

    report.working_proxies = [
        {"proxy": h.proxy, "latency_ms": h.latency_ms, "https_ok": h.https_ok, "exit_ip": h.exit_ip}
        for h in sorted(hits, key=lambda x: x.latency_ms)
    ]

    return report


def report_to_md(cfg: SourceConfig, report: SourceReport) -> str:
    lines = [
        f"# {cfg.platform} — {cfg.protocol_label}",
        "",
        f"- **Source ID**: `{cfg.id}`",
        f"- **URL**: `{cfg.url}`",
        f"- **Scheme**: {cfg.scheme}",
        f"- **更新频率**: {cfg.update_frequency or '未知'}",
        f"- **测试时间**: {report.tested_at}",
        f"- **验证端点**: `{TEST_HTTP}` / `{TEST_HTTPS}`",
        f"- **抽样上限**: {cfg.max_test}（列表大于此数时随机抽样）",
        "",
    ]
    if cfg.notes:
        lines.extend([f"> {cfg.notes}", ""])

    if not report.fetch_ok:
        lines.extend(["## 拉取失败", "", f"**错误**: {report.fetch_error}", ""])
        return "\n".join(lines)

    lines.extend([
        "## 统计",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| 拉取数量 | {report.total_fetched} |",
        f"| 测试数量 | {report.total_tested} |",
        f"| 可用数量 | {report.working} |",
        f"| 成功率 | **{report.success_rate}%** |",
        f"| HTTPS 可用 | {report.https_working} |",
        f"| 拉取耗时 | {report.fetch_ms}ms |",
    ])
    if report.median_latency_ms:
        lines.append(f"| 中位延迟 | {report.median_latency_ms}ms |")
        lines.append(f"| 平均延迟 | {report.avg_latency_ms}ms |")

    lines.extend(["", "## 可用代理", ""])
    if report.working_proxies:
        lines.extend([
            "| 代理 | 延迟(ms) | HTTPS | 出口IP |",
            "|------|----------|-------|--------|",
        ])
        for p in report.working_proxies[:20]:
            https = "✓" if p["https_ok"] else "✗"
            lines.append(f"| `{p['proxy']}` | {p['latency_ms']} | {https} | {p['exit_ip']} |")
        if len(report.working_proxies) > 20:
            lines.append(f"\n*另有 {len(report.working_proxies) - 20} 个，见同名 .json*")
    else:
        lines.append("无")

    return "\n".join(lines)


def save_report(cfg: SourceConfig, report: SourceReport) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {**asdict(report), "config": asdict(cfg)}
    (RESULTS_DIR / f"{cfg.id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / f"{cfg.id}.md").write_text(
        report_to_md(cfg, report), encoding="utf-8"
    )