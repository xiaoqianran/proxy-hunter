#!/usr/bin/env python3
"""Test free proxy sources: fetch, validate, and compare quality."""

from __future__ import annotations

import asyncio
import json
import re
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TEST_URL_HTTP = "http://httpbin.org/ip"
TEST_URL_HTTPS = "https://httpbin.org/ip"
SAMPLE_SIZE = 30          # max proxies to test per source
VALIDATE_TIMEOUT = 6      # seconds per proxy
MAX_CONCURRENT_VALIDATE = 20
LIB_COLLECT_LIMIT = 5     # free-proxy lib is slow; collect fewer
FETCH_TIMEOUT = 20

OUTPUT_DIR = Path(__file__).parent / "results"


@dataclass
class ProxyResult:
    proxy: str
    ok: bool
    latency_ms: float | None = None
    status_code: int | None = None
    error: str | None = None
    exit_ip: str | None = None
    https_ok: bool = False


@dataclass
class SourceReport:
    name: str
    url: str
    fetch_ok: bool = False
    fetch_error: str | None = None
    fetch_latency_ms: float | None = None
    total_fetched: int = 0
    tested: int = 0
    working: int = 0
    https_working: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float | None = None
    median_latency_ms: float | None = None
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    working_proxies: list[dict[str, Any]] = field(default_factory=list)
    sample_errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

async def _fetch_text(session: aiohttp.ClientSession, url: str) -> tuple[str | None, str | None, float]:
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            text = await resp.text()
            if resp.status != 200:
                return None, f"HTTP {resp.status}", (time.perf_counter() - start) * 1000
            return text, None, (time.perf_counter() - start) * 1000
    except Exception as e:
        return None, str(e), (time.perf_counter() - start) * 1000


def _parse_ip_port_lines(text: str, scheme: str = "http") -> list[str]:
    proxies = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "://" in line:
            proxies.append(line)
        elif re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
            proxies.append(f"{scheme}://{line}")
    return proxies


async def fetch_proxyscrape_http(session: aiohttp.ClientSession) -> SourceReport:
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all"
    report = SourceReport(name="ProxyScrape API (HTTP)", url=url)
    text, err, lat = await _fetch_text(session, url)
    report.fetch_latency_ms = round(lat, 1)
    if err:
        report.fetch_error = err
        return report
    report.fetch_ok = True
    proxies = _parse_ip_port_lines(text)
    report.total_fetched = len(proxies)
    return report, proxies


async def fetch_proxyscrape_socks5(session: aiohttp.ClientSession) -> SourceReport:
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all"
    report = SourceReport(name="ProxyScrape API (SOCKS5)", url=url)
    text, err, lat = await _fetch_text(session, url)
    report.fetch_latency_ms = round(lat, 1)
    if err:
        report.fetch_error = err
        return report
    report.fetch_ok = True
    proxies = _parse_ip_port_lines(text, scheme="socks5")
    report.total_fetched = len(proxies)
    return report, proxies


async def fetch_proxifly_github(session: aiohttp.ClientSession) -> SourceReport:
    url = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.json"
    report = SourceReport(name="GitHub proxifly/free-proxy-list", url=url)
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
            if resp.status != 200:
                report.fetch_error = f"HTTP {resp.status}"
                return report
            raw = await resp.text()
            data = json.loads(raw)
            report.fetch_ok = True
            proxies = [item["proxy"] for item in data if "proxy" in item]
            report.total_fetched = len(proxies)
            return report, proxies
    except Exception as e:
        report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
        report.fetch_error = str(e)
        return report


async def fetch_geonode(session: aiohttp.ClientSession) -> SourceReport:
    url = (
        "https://proxylist.geonode.com/api/proxy-list"
        "?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols=http,socks5"
    )
    report = SourceReport(name="Geonode API", url=url)
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
            if resp.status != 200:
                report.fetch_error = f"HTTP {resp.status}"
                return report
            payload = await resp.json()
            report.fetch_ok = True
            proxies = []
            for item in payload.get("data", []):
                proto = item.get("protocols", ["http"])[0]
                proxies.append(f"{proto}://{item['ip']}:{item['port']}")
            report.total_fetched = len(proxies)
            return report, proxies
    except Exception as e:
        report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
        report.fetch_error = str(e)
        return report


async def fetch_iplocate_github(session: aiohttp.ClientSession) -> SourceReport:
    url = "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/all-proxies.txt"
    report = SourceReport(name="GitHub iplocate/free-proxy-list", url=url)
    text, err, lat = await _fetch_text(session, url)
    report.fetch_latency_ms = round(lat, 1)
    if err:
        report.fetch_error = err
        return report
    report.fetch_ok = True
    proxies = []
    for line in text.splitlines():
        line = line.strip()
        if line and "://" in line:
            proxies.append(line)
    report.total_fetched = len(proxies)
    return report, proxies


async def fetch_free_proxy_list_net(session: aiohttp.ClientSession) -> SourceReport:
    url = "https://free-proxy-list.net/"
    report = SourceReport(name="free-proxy-list.net", url=url)
    start = time.perf_counter()
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT),
            allow_redirects=True,
        ) as resp:
            html = await resp.text()
            report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
            if resp.status != 200:
                report.fetch_error = f"HTTP {resp.status}"
                return report
            soup = BeautifulSoup(html, "lxml")
            proxies = []
            for row in soup.select("table tbody tr"):
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue
                ip = cols[0].get_text(strip=True)
                port = cols[1].get_text(strip=True)
                https = cols[6].get_text(strip=True).lower() == "yes"
                scheme = "https" if https else "http"
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip) and port.isdigit():
                    proxies.append(f"{scheme}://{ip}:{port}")
            report.fetch_ok = True
            report.total_fetched = len(proxies)
            return report, proxies
    except Exception as e:
        report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
        report.fetch_error = str(e)
        return report


def fetch_free_proxy_lib() -> tuple[SourceReport, list[str]]:
    """free-proxy PyPI library - runs synchronously, pre-validated."""
    report = SourceReport(
        name="free-proxy (PyPI library)",
        url="https://pypi.org/project/free-proxy/",
    )
    proxies = []
    start = time.perf_counter()
    try:
        from fp.fp import FreeProxy

        report.fetch_ok = True
        # Library returns one working proxy per call; keep attempts bounded
        seen = set()
        attempts = 0
        max_attempts = LIB_COLLECT_LIMIT * 4
        while len(proxies) < LIB_COLLECT_LIMIT and attempts < max_attempts:
            attempts += 1
            try:
                p = FreeProxy(rand=True, timeout=2, anonym=True).get()
                if p and p not in seen:
                    seen.add(p)
                    proxies.append(p)
            except Exception:
                continue
        report.total_fetched = len(proxies)
        report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
        if not proxies:
            report.fetch_error = "No working proxy returned by library"
            report.fetch_ok = False
        return report, proxies
    except Exception as e:
        report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
        report.fetch_error = str(e)
        return report


def fetch_proxyscrape_lib() -> tuple[SourceReport, list[str]]:
    report = SourceReport(
        name="proxyscrape (PyPI library)",
        url="https://pypi.org/project/proxyscrape/",
    )
    proxies = []
    start = time.perf_counter()
    try:
        from proxyscrape import create_collector

        collector = create_collector("proxy-test", "http")
        seen = set()
        for _ in range(LIB_COLLECT_LIMIT * 3):
            proxy = collector.get_proxy()
            if proxy is None:
                break
            url = f"http://{proxy.host}:{proxy.port}"
            if url not in seen:
                seen.add(url)
                proxies.append(url)
            if len(proxies) >= LIB_COLLECT_LIMIT:
                break
        report.fetch_ok = True
        report.total_fetched = len(proxies)
        report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return report, proxies
    except Exception as e:
        report.fetch_latency_ms = round((time.perf_counter() - start) * 1000, 1)
        report.fetch_error = str(e)
        return report


async def fetch_tor() -> tuple[SourceReport, list[str]]:
    report = SourceReport(name="Tor (local SOCKS5)", url="socks5h://127.0.0.1:9050")
    proxies = ["socks5://127.0.0.1:9050"]
    report.fetch_ok = True
    report.total_fetched = 1
    report.fetch_latency_ms = 0
    return report, proxies


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

async def _test_single_proxy(proxy: str, sem: asyncio.Semaphore) -> ProxyResult:
    async with sem:
        start = time.perf_counter()
        is_socks = proxy.startswith("socks5")

        # HTTP test
        try:
            if is_socks:
                connector = ProxyConnector.from_url(proxy)
                async with aiohttp.ClientSession(connector=connector) as sess:
                    async with sess.get(
                        TEST_URL_HTTP,
                        timeout=aiohttp.ClientTimeout(total=VALIDATE_TIMEOUT),
                    ) as resp:
                        latency = (time.perf_counter() - start) * 1000
                        body = await resp.json()
                        exit_ip = body.get("origin", "").split(",")[0].strip()
                        result = ProxyResult(
                            proxy=proxy,
                            ok=resp.status == 200,
                            latency_ms=round(latency, 1),
                            status_code=resp.status,
                            exit_ip=exit_ip,
                        )
            else:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(
                        TEST_URL_HTTP,
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=VALIDATE_TIMEOUT),
                    ) as resp:
                        latency = (time.perf_counter() - start) * 1000
                        body = await resp.json()
                        exit_ip = body.get("origin", "").split(",")[0].strip()
                        result = ProxyResult(
                            proxy=proxy,
                            ok=resp.status == 200,
                            latency_ms=round(latency, 1),
                            status_code=resp.status,
                            exit_ip=exit_ip,
                        )
        except Exception as e:
            return ProxyResult(proxy=proxy, ok=False, error=str(e)[:120])

        # HTTPS test (only if HTTP succeeded)
        if result.ok:
            start2 = time.perf_counter()
            try:
                if is_socks:
                    connector = ProxyConnector.from_url(proxy)
                    async with aiohttp.ClientSession(connector=connector) as sess:
                        async with sess.get(
                            TEST_URL_HTTPS,
                            timeout=aiohttp.ClientTimeout(total=VALIDATE_TIMEOUT),
                        ) as resp:
                            result.https_ok = resp.status == 200
                else:
                    async with aiohttp.ClientSession() as sess:
                        async with sess.get(
                            TEST_URL_HTTPS,
                            proxy=proxy,
                            timeout=aiohttp.ClientTimeout(total=VALIDATE_TIMEOUT),
                        ) as resp:
                            result.https_ok = resp.status == 200
            except Exception:
                result.https_ok = False

        return result


async def validate_proxies(proxies: list[str]) -> list[ProxyResult]:
    sample = proxies[:SAMPLE_SIZE]
    sem = asyncio.Semaphore(MAX_CONCURRENT_VALIDATE)
    tasks = [_test_single_proxy(p, sem) for p in sample]
    return await asyncio.gather(*tasks)


def finalize_report(report: SourceReport, results: list[ProxyResult]) -> SourceReport:
    report.tested = len(results)
    working = [r for r in results if r.ok]
    report.working = len(working)
    report.https_working = sum(1 for r in working if r.https_ok)
    report.success_rate = round(report.working / report.tested * 100, 1) if report.tested else 0.0

    latencies = [r.latency_ms for r in working if r.latency_ms is not None]
    if latencies:
        report.avg_latency_ms = round(statistics.mean(latencies), 1)
        report.median_latency_ms = round(statistics.median(latencies), 1)
        report.min_latency_ms = round(min(latencies), 1)
        report.max_latency_ms = round(max(latencies), 1)

    report.working_proxies = [
        {
            "proxy": r.proxy,
            "latency_ms": r.latency_ms,
            "exit_ip": r.exit_ip,
            "https_ok": r.https_ok,
        }
        for r in sorted(working, key=lambda x: x.latency_ms or 9999)
    ]

    errors = [r.error for r in results if not r.ok and r.error]
    report.sample_errors = list(dict.fromkeys(errors))[:5]
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_source(
    session: aiohttp.ClientSession,
    fetcher,
    is_async: bool = True,
    skip_validate: bool = False,
) -> SourceReport:
    result = await fetcher(session) if is_async else fetcher()
    if isinstance(result, tuple):
        report, proxies = result
    else:
        return result

    if not report.fetch_ok or not proxies:
        return report

    if skip_validate:
        return report

    print(f"  验证 {min(len(proxies), SAMPLE_SIZE)}/{report.total_fetched} 个代理...")
    validation_results = await validate_proxies(proxies)
    return finalize_report(report, validation_results)


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("免费代理源质量测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"每源抽样: {SAMPLE_SIZE} | 超时: {VALIDATE_TIMEOUT}s")
    print("=" * 60)

    async_fetchers = [
        ("ProxyScrape HTTP", fetch_proxyscrape_http),
        ("ProxyScrape SOCKS5", fetch_proxyscrape_socks5),
        ("proxifly GitHub", fetch_proxifly_github),
        ("Geonode API", fetch_geonode),
        ("iplocate GitHub", fetch_iplocate_github),
        ("free-proxy-list.net", fetch_free_proxy_list_net),
    ]

    sync_fetchers = [
        ("free-proxy lib", fetch_free_proxy_lib),
        ("proxyscrape lib", fetch_proxyscrape_lib),
    ]

    reports: list[SourceReport] = []

    async with aiohttp.ClientSession(
        headers={"User-Agent": "ProxyQualityTest/1.0 (Research)"}
    ) as session:
        for name, fetcher in async_fetchers:
            print(f"\n[{name}] 拉取中...", flush=True)
            report = await run_source(session, fetcher)
            reports.append(report)
            _print_source_summary(report)

        for name, fetcher in sync_fetchers:
            print(f"\n[{name}] 拉取中...", flush=True)
            try:
                report = await asyncio.wait_for(
                    run_source(session, fetcher, is_async=False),
                    timeout=90,
                )
            except asyncio.TimeoutError:
                report = SourceReport(
                    name=fetcher.__name__.replace("fetch_", "").replace("_", " "),
                    url="(library)",
                    fetch_error="拉取超时 (>90s)",
                )
                if name == "free-proxy lib":
                    report.name = "free-proxy (PyPI library)"
                    report.url = "https://pypi.org/project/free-proxy/"
                elif name == "proxyscrape lib":
                    report.name = "proxyscrape (PyPI library)"
                    report.url = "https://pypi.org/project/proxyscrape/"
            reports.append(report)
            _print_source_summary(report)

        print(f"\n[Tor] 检测本地 Tor...")
        tor_report, tor_proxies = await fetch_tor()
        tor_results = await validate_proxies(tor_proxies)
        tor_report = finalize_report(tor_report, tor_results)
        if not tor_report.working:
            tor_report.fetch_error = "Tor 未运行 (127.0.0.1:9050 不可达)"
        reports.append(tor_report)
        _print_source_summary(tor_report)

    # Save JSON report
    json_path = OUTPUT_DIR / f"report_{timestamp}.json"
    summary = {
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": SAMPLE_SIZE,
        "validate_timeout_s": VALIDATE_TIMEOUT,
        "test_urls": {"http": TEST_URL_HTTP, "https": TEST_URL_HTTPS},
        "sources": [asdict(r) for r in reports],
        "ranking": _build_ranking(reports),
    }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save markdown summary
    md_path = OUTPUT_DIR / f"report_{timestamp}.md"
    md_path.write_text(_build_markdown(summary), encoding="utf-8")

    print("\n" + "=" * 60)
    print("综合排名 (按成功率 → 延迟)")
    print("=" * 60)
    for i, row in enumerate(summary["ranking"], 1):
        print(
            f"  {i}. {row['name']}: "
            f"成功率 {row['success_rate']}% | "
            f"可用 {row['working']}/{row['tested']} | "
            f"HTTPS {row['https_working']} | "
            f"中位延迟 {row['median_latency_ms'] or 'N/A'}ms"
        )

    print(f"\n报告已保存:")
    print(f"  {json_path}")
    print(f"  {md_path}")


def _print_source_summary(report: SourceReport):
    if not report.fetch_ok:
        print(f"  ✗ 拉取失败: {report.fetch_error}")
        return
    print(f"  ✓ 拉取成功: {report.total_fetched} 个代理 ({report.fetch_latency_ms}ms)")
    if report.tested:
        print(
            f"  验证结果: {report.working}/{report.tested} 可用 "
            f"({report.success_rate}%), HTTPS: {report.https_working}"
        )
        if report.median_latency_ms:
            print(
                f"  延迟: 中位 {report.median_latency_ms}ms, "
                f"平均 {report.avg_latency_ms}ms, "
                f"范围 {report.min_latency_ms}-{report.max_latency_ms}ms"
            )
        if report.working_proxies:
            best = report.working_proxies[0]
            print(f"  最快: {best['proxy']} ({best['latency_ms']}ms, IP={best['exit_ip']})")


def _build_ranking(reports: list[SourceReport]) -> list[dict]:
    ranked = []
    for r in reports:
        if not r.fetch_ok or r.tested == 0:
            continue
        ranked.append({
            "name": r.name,
            "success_rate": r.success_rate,
            "working": r.working,
            "tested": r.tested,
            "https_working": r.https_working,
            "median_latency_ms": r.median_latency_ms,
            "total_fetched": r.total_fetched,
        })
    ranked.sort(
        key=lambda x: (-x["success_rate"], x["median_latency_ms"] or 99999)
    )
    return ranked


def _build_markdown(summary: dict) -> str:
    lines = [
        "# 免费代理源质量测试报告",
        "",
        f"- **测试时间**: {summary['tested_at']}",
        f"- **每源抽样**: {summary['sample_size']} 个",
        f"- **验证超时**: {summary['validate_timeout_s']}s",
        f"- **测试 URL**: {summary['test_urls']['http']}",
        "",
        "## 综合排名",
        "",
        "| 排名 | 来源 | 拉取数 | 测试数 | 可用 | 成功率 | HTTPS可用 | 中位延迟(ms) |",
        "|------|------|--------|--------|------|--------|-----------|-------------|",
    ]

    for i, row in enumerate(summary["ranking"], 1):
        med = row["median_latency_ms"] if row["median_latency_ms"] else "N/A"
        lines.append(
            f"| {i} | {row['name']} | {row['total_fetched']} | {row['tested']} | "
            f"{row['working']} | {row['success_rate']}% | {row['https_working']} | {med} |"
        )

    lines.extend(["", "## 各源详情", ""])

    for src in summary["sources"]:
        lines.append(f"### {src['name']}")
        lines.append(f"- URL: `{src['url']}`")
        if not src["fetch_ok"]:
            lines.append(f"- **拉取失败**: {src['fetch_error']}")
            lines.append("")
            continue
        lines.append(f"- 拉取: {src['total_fetched']} 个 ({src['fetch_latency_ms']}ms)")
        lines.append(
            f"- 验证: {src['working']}/{src['tested']} 可用 ({src['success_rate']}%)"
        )
        if src["avg_latency_ms"]:
            lines.append(
                f"- 延迟: 平均 {src['avg_latency_ms']}ms, "
                f"中位 {src['median_latency_ms']}ms, "
                f"范围 {src['min_latency_ms']}-{src['max_latency_ms']}ms"
            )
        if src["working_proxies"]:
            lines.append("- 可用代理 (按速度排序):")
            for p in src["working_proxies"][:5]:
                https = "✓" if p["https_ok"] else "✗"
                lines.append(
                    f"  - `{p['proxy']}` — {p['latency_ms']}ms, "
                    f"出口IP={p['exit_ip']}, HTTPS={https}"
                )
        if src["sample_errors"]:
            lines.append("- 常见错误:")
            for e in src["sample_errors"]:
                lines.append(f"  - `{e}`")
        lines.append("")

    lines.extend([
        "## 结论",
        "",
        "免费代理整体成功率通常较低（<20%），适合学习测试，不适合生产环境。",
        "如需稳定爬取，建议使用付费旋转代理或 ScraperAPI 等服务的免费额度。",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())