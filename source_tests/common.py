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
from typing import Any, Callable

import aiohttp
from aiohttp_socks import ProxyConnector

ROOT = Path(__file__).parent
SOURCES_DIR = ROOT / "sources"
RESULTS_DIR = ROOT / "results"
CACHE_DIR = ROOT / ".cache"

TEST_HTTP = "http://icanhazip.com"
TEST_HTTPS = "https://icanhazip.com"

IP_PORT = re.compile(r"^\d+\.\d+\.\d+\.\d+:\d+$")
IP_IN_LINE = re.compile(r"^\d+\.\d+\.\d+\.\d+:\d+")


@dataclass
class TestSettings:
    timeout: float = 6.0
    connect_timeout: float = 3.0
    concurrency: int = 40
    max_test: int = 50
    check_https: bool = True
    https_only_for_hits: bool = True  # skip HTTPS probe when HTTP fails


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
    max_test: int = 50

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
    validate_ms: float | None = None
    total_fetched: int = 0
    total_tested: int = 0
    working: int = 0
    https_working: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float | None = None
    median_latency_ms: float | None = None
    working_proxies: list[dict[str, Any]] = field(default_factory=list)
    sample_errors: list[str] = field(default_factory=list)


def _timeout(settings: TestSettings) -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(
        total=settings.timeout,
        connect=settings.connect_timeout,
        sock_connect=settings.connect_timeout,
    )


def parse_body(text: str, scheme: str, fmt: str) -> list[str]:
    proxies: list[str] = []
    if fmt == "json":
        data = json.loads(text)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    proxies.append(item if "://" in item else f"{scheme}://{item}")
                elif isinstance(item, dict):
                    p = item.get("proxy")
                    if p and "://" in str(p):
                        proxies.append(str(p))
                    elif item.get("ip") and item.get("port"):
                        proxies.append(f"{scheme}://{item['ip']}:{item['port']}")
        return _dedupe(proxies)

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "://" in line:
            proxies.append(line.split()[0] if " " in line else line)
        elif IP_PORT.match(line) or IP_IN_LINE.match(line):
            hostport = line.split()[0] if " " in line else line
            proxies.append(f"{scheme}://{hostport}")
    return _dedupe(proxies)


def _dedupe(proxies: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in proxies:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


async def fetch_list(
    cfg: SourceConfig,
    session: aiohttp.ClientSession | None = None,
    use_cache: bool = True,
) -> tuple[list[str], str | None, float]:
    cache_path = CACHE_DIR / f"{cfg.id}.txt"
    if use_cache and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 3600:
            text = cache_path.read_text(encoding="utf-8")
            proxies = parse_body(text, cfg.scheme, cfg.format)
            return proxies, None, 0.0

    start = time.perf_counter()

    async def _get(sess: aiohttp.ClientSession) -> tuple[list[str], str | None, float]:
        try:
            async with sess.get(cfg.url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                ms = (time.perf_counter() - start) * 1000
                if resp.status != 200:
                    return [], f"HTTP {resp.status}", ms
                text = await resp.text()
                if use_cache:
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(text, encoding="utf-8")
                return parse_body(text, cfg.scheme, cfg.format), None, ms
        except Exception as e:
            return [], str(e)[:200], (time.perf_counter() - start) * 1000

    if session:
        return await _get(session)
    async with aiohttp.ClientSession(
        headers={"User-Agent": "ProxyHunter-SourceTest/2.0"},
        connector=aiohttp.TCPConnector(limit=20, ttl_dns_cache=300),
    ) as sess:
        return await _get(sess)


async def _test_http_http(
    session: aiohttp.ClientSession,
    proxy: str,
    settings: TestSettings,
) -> tuple[str, float, str] | None:
    try:
        t0 = time.perf_counter()
        async with session.get(TEST_HTTP, proxy=proxy, timeout=_timeout(settings)) as resp:
            if resp.status != 200:
                return None
            ip = (await resp.text()).strip()[:60]
            return proxy, round((time.perf_counter() - t0) * 1000, 1), ip
    except Exception:
        return None


async def _test_http_https(
    session: aiohttp.ClientSession,
    proxy: str,
    settings: TestSettings,
) -> bool:
    try:
        async with session.get(TEST_HTTPS, proxy=proxy, timeout=_timeout(settings)) as resp:
            return resp.status == 200
    except Exception:
        return False


async def _test_socks_http(
    proxy: str,
    settings: TestSettings,
) -> tuple[str, float, str] | None:
    try:
        connector = ProxyConnector.from_url(proxy, rdns=True)
        async with aiohttp.ClientSession(connector=connector, timeout=_timeout(settings)) as session:
            t0 = time.perf_counter()
            async with session.get(TEST_HTTP, timeout=_timeout(settings)) as resp:
                if resp.status != 200:
                    return None
                ip = (await resp.text()).strip()[:60]
                return proxy, round((time.perf_counter() - t0) * 1000, 1), ip
    except Exception:
        return None


async def _test_socks_https(proxy: str, settings: TestSettings) -> bool:
    try:
        connector = ProxyConnector.from_url(proxy, rdns=True)
        async with aiohttp.ClientSession(connector=connector, timeout=_timeout(settings)) as session:
            async with session.get(TEST_HTTPS, timeout=_timeout(settings)) as resp:
                return resp.status == 200
    except Exception:
        return False


async def validate_proxies(
    proxies: list[str],
    settings: TestSettings,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[ProxyHit]:
    sem = asyncio.Semaphore(settings.concurrency)
    http_hits: list[tuple[str, float, str]] = []
    done = 0
    total = len(proxies)

    http_proxies = [p for p in proxies if not p.startswith("socks")]
    socks_proxies = [p for p in proxies if p.startswith("socks")]

    async def run_http_batch() -> None:
        nonlocal done
        connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300, enable_cleanup_closed=True)
        async with aiohttp.ClientSession(connector=connector, timeout=_timeout(settings)) as session:

            async def one(proxy: str) -> None:
                nonlocal done
                async with sem:
                    hit = await _test_http_http(session, proxy, settings)
                    done += 1
                    if on_progress and done % 10 == 0:
                        on_progress(done, total)
                    if hit:
                        http_hits.append(hit)

            await asyncio.gather(*[one(p) for p in http_proxies])

    async def run_socks_batch() -> None:
        nonlocal done

        async def one(proxy: str) -> None:
            nonlocal done
            async with sem:
                hit = await _test_socks_http(proxy, settings)
                done += 1
                if on_progress and done % 10 == 0:
                    on_progress(done, total)
                if hit:
                    http_hits.append(hit)

        await asyncio.gather(*[one(p) for p in socks_proxies])

    await asyncio.gather(run_http_batch(), run_socks_batch())

    if on_progress:
        on_progress(total, total)

    if not settings.check_https or not http_hits:
        return [ProxyHit(p, lat, False, ip) for p, lat, ip in http_hits]

    https_map: dict[str, bool] = {}

    if http_proxies:
        connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector, timeout=_timeout(settings)) as session:

            async def https_one(proxy: str) -> None:
                async with sem:
                    https_map[proxy] = await _test_http_https(session, proxy, settings)

            await asyncio.gather(*[https_one(p) for p, _, _ in http_hits if not p.startswith("socks")])

    socks_to_check = [p for p, _, _ in http_hits if p.startswith("socks")]
    if socks_to_check:

        async def socks_https_one(proxy: str) -> None:
            async with sem:
                https_map[proxy] = await _test_socks_https(proxy, settings)

        await asyncio.gather(*[socks_https_one(p) for p in socks_to_check])

    return [
        ProxyHit(p, lat, https_map.get(p, False), ip)
        for p, lat, ip in http_hits
    ]


async def run_source_test(
    cfg: SourceConfig,
    settings: TestSettings | None = None,
    use_cache: bool = True,
    on_progress: Callable[[int, int], None] | None = None,
) -> SourceReport:
    settings = settings or TestSettings(max_test=cfg.max_test)

    report = SourceReport(
        source_id=cfg.id,
        platform=cfg.platform,
        protocol_label=cfg.protocol_label,
        url=cfg.url,
        tested_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    )

    proxies, err, fetch_ms = await fetch_list(cfg, use_cache=use_cache)
    report.fetch_ms = round(fetch_ms, 1)
    report.total_fetched = len(proxies)

    if err:
        report.fetch_error = err
        return report

    report.fetch_ok = True
    if not proxies:
        report.fetch_error = "Empty proxy list"
        return report

    sample = random.sample(proxies, settings.max_test) if len(proxies) > settings.max_test else proxies
    report.total_tested = len(sample)

    t0 = time.perf_counter()
    hits = await validate_proxies(sample, settings, on_progress=on_progress)
    report.validate_ms = round((time.perf_counter() - t0) * 1000, 1)

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


def report_to_md(cfg: SourceConfig, report: SourceReport, settings: TestSettings | None = None) -> str:
    settings = settings or TestSettings()
    lines = [
        f"# {cfg.platform} — {cfg.protocol_label}",
        "",
        f"- **Source ID**: `{cfg.id}`",
        f"- **URL**: `{cfg.url}`",
        f"- **Scheme**: {cfg.scheme}",
        f"- **更新频率**: {cfg.update_frequency or '未知'}",
        f"- **测试时间**: {report.tested_at}",
        f"- **验证端点**: `{TEST_HTTP}` / `{TEST_HTTPS}`",
        f"- **抽样上限**: {cfg.max_test}",
        f"- **并发/超时**: {settings.concurrency} / {settings.timeout}s",
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
        f"| 验证耗时 | {report.validate_ms}ms |",
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


def save_report(cfg: SourceConfig, report: SourceReport, settings: TestSettings | None = None) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    settings = settings or TestSettings()
    payload = {**asdict(report), "config": asdict(cfg), "settings": asdict(settings)}
    (RESULTS_DIR / f"{cfg.id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / f"{cfg.id}.md").write_text(
        report_to_md(cfg, report, settings), encoding="utf-8"
    )


def result_is_fresh(source_id: str, max_age_sec: int = 3600) -> bool:
    path = RESULTS_DIR / f"{source_id}.json"
    if not path.exists():
        return False
    return time.time() - path.stat().st_mtime < max_age_sec