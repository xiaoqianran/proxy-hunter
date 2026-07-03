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
UA = "ProxyHunter-SourceTest/3.0"

IP_PORT = re.compile(r"^\d+\.\d+\.\d+\.\d+:\d+$")
IP_IN_LINE = re.compile(r"^\d+\.\d+\.\d+\.\d+:\d+")


def install_uvloop() -> bool:
    try:
        import uvloop
        uvloop.install()
        return True
    except ImportError:
        return False


@dataclass
class TestSettings:
    timeout: float = 4.0
    connect_timeout: float = 2.0
    concurrency: int = 80
    max_test: int = 50
    check_https: bool = True
    https_only_for_hits: bool = True


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
        sock_read=settings.timeout,
    )


def _http_connector() -> aiohttp.TCPConnector:
    return aiohttp.TCPConnector(
        limit=0,
        ttl_dns_cache=600,
        enable_cleanup_closed=True,
        force_close=True,
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


def _cache_paths(cfg: SourceConfig) -> tuple[Path, Path]:
    return CACHE_DIR / f"{cfg.id}.txt", CACHE_DIR / f"{cfg.id}.proxies.json"


def _load_cached_proxies(cfg: SourceConfig) -> list[str] | None:
    raw_path, parsed_path = _cache_paths(cfg)
    for path in (parsed_path, raw_path):
        if not path.exists():
            continue
        age = time.time() - path.stat().st_mtime
        if age >= 3600:
            continue
        if path is parsed_path:
            return json.loads(path.read_text(encoding="utf-8"))
        text = path.read_text(encoding="utf-8")
        proxies = parse_body(text, cfg.scheme, cfg.format)
        try:
            parsed_path.write_text(json.dumps(proxies), encoding="utf-8")
        except OSError:
            pass
        return proxies
    return None


def _store_cache(cfg: SourceConfig, text: str, proxies: list[str]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    raw_path, parsed_path = _cache_paths(cfg)
    raw_path.write_text(text, encoding="utf-8")
    parsed_path.write_text(json.dumps(proxies), encoding="utf-8")


async def fetch_list(
    cfg: SourceConfig,
    session: aiohttp.ClientSession | None = None,
    use_cache: bool = True,
) -> tuple[list[str], str | None, float]:
    if use_cache:
        cached = _load_cached_proxies(cfg)
        if cached is not None:
            return cached, None, 0.0

    start = time.perf_counter()

    async def _get(sess: aiohttp.ClientSession) -> tuple[list[str], str | None, float]:
        try:
            async with sess.get(cfg.url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                ms = (time.perf_counter() - start) * 1000
                if resp.status != 200:
                    return [], f"HTTP {resp.status}", ms
                text = await resp.text()
                proxies = parse_body(text, cfg.scheme, cfg.format)
                if use_cache:
                    _store_cache(cfg, text, proxies)
                return proxies, None, ms
        except Exception as e:
            return [], str(e)[:200], (time.perf_counter() - start) * 1000

    if session:
        return await _get(session)
    async with aiohttp.ClientSession(
        headers={"User-Agent": UA},
        connector=aiohttp.TCPConnector(limit=32, ttl_dns_cache=300, force_close=True),
    ) as sess:
        return await _get(sess)


async def prefetch_lists(
    configs: list[SourceConfig],
    use_cache: bool = True,
    workers: int = 16,
) -> None:
    if not configs:
        return
    sem = asyncio.Semaphore(workers)
    connector = aiohttp.TCPConnector(limit=workers * 2, ttl_dns_cache=300, force_close=True)
    async with aiohttp.ClientSession(headers={"User-Agent": UA}, connector=connector) as session:

        async def one(cfg: SourceConfig) -> None:
            async with sem:
                await fetch_list(cfg, session=session, use_cache=use_cache)

        await asyncio.gather(*[one(cfg) for cfg in configs])


async def _read_exit_ip(resp: aiohttp.ClientResponse) -> str:
    chunk = await resp.content.read(96)
    return chunk.decode("utf-8", errors="ignore").strip()[:60]


async def _test_http_proxy(
    session: aiohttp.ClientSession,
    proxy: str,
    settings: TestSettings,
) -> ProxyHit | None:
    try:
        t0 = time.perf_counter()
        async with session.get(TEST_HTTP, proxy=proxy, timeout=_timeout(settings)) as resp:
            if resp.status != 200:
                return None
            ip = await _read_exit_ip(resp)
            latency = round((time.perf_counter() - t0) * 1000, 1)
            https_ok = False
            if settings.check_https:
                try:
                    async with session.get(TEST_HTTPS, proxy=proxy, timeout=_timeout(settings)) as hres:
                        https_ok = hres.status == 200
                except Exception:
                    pass
            return ProxyHit(proxy, latency, https_ok, ip)
    except Exception:
        return None


async def _test_socks_proxy(proxy: str, settings: TestSettings) -> ProxyHit | None:
    connector = ProxyConnector.from_url(proxy, rdns=True)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=_timeout(settings)) as session:
            t0 = time.perf_counter()
            async with session.get(TEST_HTTP, timeout=_timeout(settings)) as resp:
                if resp.status != 200:
                    return None
                ip = await _read_exit_ip(resp)
                latency = round((time.perf_counter() - t0) * 1000, 1)
                https_ok = False
                if settings.check_https:
                    try:
                        async with session.get(TEST_HTTPS, timeout=_timeout(settings)) as hres:
                            https_ok = hres.status == 200
                    except Exception:
                        pass
                return ProxyHit(proxy, latency, https_ok, ip)
    except Exception:
        return None
    finally:
        await connector.close()


async def validate_proxies(
    proxies: list[str],
    settings: TestSettings,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[ProxyHit]:
    if not proxies:
        return []

    sem = asyncio.Semaphore(settings.concurrency)
    total = len(proxies)
    done = 0
    lock = asyncio.Lock()
    hits: list[ProxyHit] = []

    http_proxies = [p for p in proxies if not p.startswith("socks")]
    socks_proxies = [p for p in proxies if p.startswith("socks")]

    async def bump() -> int:
        nonlocal done
        async with lock:
            done += 1
            cur = done
        if on_progress and (cur == total or cur % 10 == 0):
            on_progress(cur, total)
        return cur

    async def run_http_batch() -> None:
        if not http_proxies:
            return
        async with aiohttp.ClientSession(connector=_http_connector(), timeout=_timeout(settings)) as session:

            async def one(proxy: str) -> None:
                async with sem:
                    hit = await _test_http_proxy(session, proxy, settings)
                    await bump()
                    if hit:
                        hits.append(hit)

            await asyncio.gather(*[one(p) for p in http_proxies])

    async def run_socks_batch() -> None:
        if not socks_proxies:
            return

        async def one(proxy: str) -> None:
            async with sem:
                hit = await _test_socks_proxy(proxy, settings)
                await bump()
                if hit:
                    hits.append(hit)

        await asyncio.gather(*[one(p) for p in socks_proxies])

    await asyncio.gather(run_http_batch(), run_socks_batch())

    if on_progress:
        on_progress(total, total)
    return hits


async def run_source_test(
    cfg: SourceConfig,
    settings: TestSettings | None = None,
    use_cache: bool = True,
    on_progress: Callable[[int, int], None] | None = None,
    fetch_session: aiohttp.ClientSession | None = None,
) -> SourceReport:
    settings = settings or TestSettings(max_test=cfg.max_test)

    report = SourceReport(
        source_id=cfg.id,
        platform=cfg.platform,
        protocol_label=cfg.protocol_label,
        url=cfg.url,
        tested_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    )

    proxies, err, fetch_ms = await fetch_list(cfg, session=fetch_session, use_cache=use_cache)
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


async def save_report_async(cfg: SourceConfig, report: SourceReport, settings: TestSettings | None = None) -> None:
    await asyncio.to_thread(save_report, cfg, report, settings)


def result_is_fresh(source_id: str, max_age_sec: int = 3600) -> bool:
    path = RESULTS_DIR / f"{source_id}.json"
    if not path.exists():
        return False
    return time.time() - path.stat().st_mtime < max_age_sec