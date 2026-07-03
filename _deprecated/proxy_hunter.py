#!/usr/bin/env python3
"""Hunt high-quality working free proxies from 20+ sources."""

from __future__ import annotations

import asyncio
import json
import re
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine

import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(__file__).parent / "results"
VALIDATE_TIMEOUT = 10
MAX_CONCURRENT_VALIDATE = 30
FETCH_TIMEOUT = 25
GEONODE_MAX_PAGES = 5

HTTP_TEST_URLS = [
    "http://icanhazip.com",
    "http://api.ipify.org",
    "http://checkip.amazonaws.com",
]
HTTPS_TEST_URL = "https://icanhazip.com"

IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IP_PORT_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+:\d+$")

PROXY_REVEAL_HEADERS = {
    "via",
    "x-forwarded-for",
    "x-real-ip",
    "proxy-connection",
    "forwarded",
}


@dataclass
class SourceResult:
    name: str
    url: str
    ok: bool = False
    error: str | None = None
    fetched: int = 0
    latency_ms: float | None = None


@dataclass
class ProxyCandidate:
    proxy: str
    sources: set[str] = field(default_factory=set)
    elite_hint: bool = False


@dataclass
class ProxyResult:
    proxy: str
    ok: bool = False
    http_ok: bool = False
    https_ok: bool = False
    latency_ms: float | None = None
    exit_ip: str | None = None
    anonymity: str = "unknown"
    score: int = 0
    sources: list[str] = field(default_factory=list)
    error: str | None = None
    round_passed: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, flush=True)


def normalize_proxy(raw: str, default_scheme: str = "http") -> str | None:
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return None
    if "://" in raw:
        return raw
    if IP_PORT_PATTERN.match(raw):
        return f"{default_scheme}://{raw}"
    return None


def parse_ip_port_lines(text: str, scheme: str = "http") -> list[str]:
    proxies: list[str] = []
    for line in text.splitlines():
        proxy = normalize_proxy(line, scheme)
        if proxy:
            proxies.append(proxy)
    return proxies


def extract_ip(text: str) -> str | None:
    text = text.strip()
    if IP_PATTERN.fullmatch(text):
        return text
    match = IP_PATTERN.search(text)
    return match.group(0) if match else None


def compute_score(
    https_ok: bool,
    latency_ms: float | None,
    anonymity: str,
) -> int:
    score = 0
    if https_ok:
        score += 2
    if latency_ms is not None:
        if latency_ms < 1000:
            score += 1
        if latency_ms < 3000:
            score += 1
    if anonymity == "elite":
        score += 1
    return score


def proxy_connector_url(proxy: str) -> str:
    if proxy.startswith("socks5h://"):
        return proxy
    if proxy.startswith("socks5://"):
        return "socks5h://" + proxy[len("socks5://") :]
    return proxy


def is_socks_proxy(proxy: str) -> bool:
    return proxy.startswith("socks4") or proxy.startswith("socks5")


# ---------------------------------------------------------------------------
# Fetch layer
# ---------------------------------------------------------------------------

async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
) -> tuple[str | None, str | None, float]:
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            text = await resp.text()
            elapsed = (time.perf_counter() - start) * 1000
            if resp.status != 200:
                return None, f"HTTP {resp.status}", elapsed
            return text, None, elapsed
    except Exception as exc:
        return None, str(exc)[:200], (time.perf_counter() - start) * 1000


async def fetch_json(
    session: aiohttp.ClientSession,
    url: str,
) -> tuple[Any | None, str | None, float]:
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            elapsed = (time.perf_counter() - start) * 1000
            if resp.status != 200:
                return None, f"HTTP {resp.status}", elapsed
            return await resp.json(), None, elapsed
    except Exception as exc:
        return None, str(exc)[:200], (time.perf_counter() - start) * 1000


async def fetch_lines_source(
    session: aiohttp.ClientSession,
    name: str,
    url: str,
    scheme: str = "http",
) -> tuple[SourceResult, list[str]]:
    text, err, lat = await fetch_text(session, url)
    result = SourceResult(name=name, url=url, latency_ms=round(lat, 1))
    if err:
        result.error = err
        return result
    proxies = parse_ip_port_lines(text, scheme)
    result.ok = True
    result.fetched = len(proxies)
    return result, proxies


async def fetch_geonode(session: aiohttp.ClientSession) -> tuple[SourceResult, list[tuple[str, bool]]]:
    name = "Geonode API (elite, google, uptime>=80)"
    base = (
        "https://proxylist.geonode.com/api/proxy-list"
        "?limit=100&sort_by=lastChecked&sort_type=desc"
        "&upTime=80&latency=500&anonymityLevel=elite&google=true"
    )
    result = SourceResult(name=name, url=base)
    proxies: list[tuple[str, bool]] = []
    seen: set[str] = set()
    total_lat = 0.0
    pages_ok = 0

    for page in range(1, GEONODE_MAX_PAGES + 1):
        url = f"{base}&page={page}"
        payload, err, lat = await fetch_json(session, url)
        total_lat += lat
        if err:
            if page == 1:
                result.error = err
                result.latency_ms = round(lat, 1)
                return result, []
            break
        pages_ok += 1
        for item in payload.get("data", []):
            ip = item.get("ip")
            port = item.get("port")
            if not ip or not port:
                continue
            proto = (item.get("protocols") or ["http"])[0]
            proxy = f"{proto}://{ip}:{port}"
            if proxy in seen:
                continue
            seen.add(proxy)
            proxies.append((proxy, True))

    if pages_ok == 0:
        return result, []

    result.ok = True
    result.fetched = len(proxies)
    result.latency_ms = round(total_lat / pages_ok, 1)
    return result, proxies


async def fetch_proxyscrape(
    session: aiohttp.ClientSession,
    protocol: str,
) -> tuple[SourceResult, list[str]]:
    url = (
        "https://api.proxyscrape.com/v2/?request=displayproxies"
        f"&protocol={protocol}&timeout=10000&country=all&ssl=all&anonymity=elite"
    )
    scheme = protocol if protocol != "http" else "http"
    text, err, lat = await fetch_text(session, url)
    result = SourceResult(name=f"ProxyScrape ({protocol.upper()} elite)", url=url, latency_ms=round(lat, 1))
    if err:
        result.error = err
        return result, []
    proxies = parse_ip_port_lines(text, scheme)
    result.ok = True
    result.fetched = len(proxies)
    return result, proxies


async def fetch_openproxylist(
    session: aiohttp.ClientSession,
    protocol: str,
) -> tuple[SourceResult, list[str]]:
    url = f"https://api.openproxylist.xyz/{protocol}.txt"
    return await fetch_lines_source(session, f"OpenProxyList ({protocol})", url, protocol)


async def fetch_proxifly(
    session: aiohttp.ClientSession,
    protocol: str,
) -> tuple[SourceResult, list[str]]:
    url = (
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/"
        f"proxies/protocols/{protocol}/data.json"
    )
    result = SourceResult(name=f"GitHub proxifly ({protocol})", url=url)
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            result.latency_ms = round((time.perf_counter() - start) * 1000, 1)
            if resp.status != 200:
                result.error = f"HTTP {resp.status}"
                return result, []
            data = await resp.json()
            proxies = [item["proxy"] for item in data if isinstance(item, dict) and item.get("proxy")]
            result.ok = True
            result.fetched = len(proxies)
            return result, proxies
    except Exception as exc:
        result.latency_ms = round((time.perf_counter() - start) * 1000, 1)
        result.error = str(exc)[:200]
        return result, []


async def fetch_iplocate(session: aiohttp.ClientSession) -> tuple[SourceResult, list[str]]:
    url = "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/all-proxies.txt"
    text, err, lat = await fetch_text(session, url)
    result = SourceResult(name="GitHub iplocate", url=url, latency_ms=round(lat, 1))
    if err:
        result.error = err
        return result, []
    proxies = []
    for line in text.splitlines():
        proxy = normalize_proxy(line)
        if proxy:
            proxies.append(proxy)
    result.ok = True
    result.fetched = len(proxies)
    return result, proxies


async def fetch_github_txt(
    session: aiohttp.ClientSession,
    name: str,
    url: str,
    scheme: str,
) -> tuple[SourceResult, list[str]]:
    return await fetch_lines_source(session, name, url, scheme)


async def fetch_free_proxy_list_net(session: aiohttp.ClientSession) -> tuple[SourceResult, list[str]]:
    url = "https://free-proxy-list.net/"
    result = SourceResult(name="free-proxy-list.net", url=url)
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            html = await resp.text()
            result.latency_ms = round((time.perf_counter() - start) * 1000, 1)
            if resp.status != 200:
                result.error = f"HTTP {resp.status}"
                return result, []
            soup = BeautifulSoup(html, "lxml")
            proxies: list[tuple[str, bool]] = []
            for row in soup.select("table tbody tr"):
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue
                ip = cols[0].get_text(strip=True)
                port = cols[1].get_text(strip=True)
                https = cols[6].get_text(strip=True).lower() == "yes"
                elite = cols[4].get_text(strip=True).lower() in {"elite proxy", "elite"}
                scheme = "https" if https else "http"
                if IP_PATTERN.fullmatch(ip) and port.isdigit():
                    proxies.append((f"{scheme}://{ip}:{port}", elite))
            result.ok = True
            result.fetched = len(proxies)
            return result, proxies
    except Exception as exc:
        result.latency_ms = round((time.perf_counter() - start) * 1000, 1)
        result.error = str(exc)[:200]
        return result, []


async def fetch_pubproxy(session: aiohttp.ClientSession) -> tuple[SourceResult, list[str]]:
    url = "http://pubproxy.com/api/proxy?limit=20&format=json&level=elite&type=http&https=true"
    result = SourceResult(name="pubproxy.com API", url=url)
    payload, err, lat = await fetch_json(session, url)
    result.latency_ms = round(lat, 1)
    if err:
        result.error = err
        return result, []
    items = payload.get("data", []) if isinstance(payload, dict) else []
    proxies = []
    for item in items:
        if not isinstance(item, dict):
            continue
        ip = item.get("ip")
        port = item.get("port")
        ptype = (item.get("type") or "http").lower()
        if ip and port:
            proxies.append(f"{ptype}://{ip}:{port}")
    result.ok = True
    result.fetched = len(proxies)
    return result, proxies


async def fetch_proxy_list_download(
    session: aiohttp.ClientSession,
    proxy_type: str,
) -> tuple[SourceResult, list[str]]:
    url = f"https://www.proxy-list.download/api/v1/get?type={proxy_type}"
    scheme = "socks5" if proxy_type == "socks5" else proxy_type
    return await fetch_lines_source(session, f"proxy-list.download ({proxy_type})", url, scheme)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

async def get_direct_ip(session: aiohttp.ClientSession) -> str | None:
    for url in HTTP_TEST_URLS:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    ip = extract_ip(await resp.text())
                    if ip:
                        return ip
        except Exception:
            continue
    return None


def classify_anonymity(
    direct_ip: str | None,
    exit_ip: str | None,
    response_headers: dict[str, str] | None,
) -> str:
    if not exit_ip:
        return "unknown"
    if direct_ip and exit_ip == direct_ip:
        return "transparent"

    if response_headers:
        lowered = {k.lower(): v for k, v in response_headers.items()}
        for header in PROXY_REVEAL_HEADERS:
            if header in lowered:
                value = lowered[header].lower()
                if direct_ip and direct_ip in value:
                    return "transparent"
                return "anonymous"

    if direct_ip and exit_ip != direct_ip:
        return "elite"
    return "anonymous"


async def _request_via_proxy(
    proxy: str,
    url: str,
    timeout: int,
) -> tuple[bool, float, str | None, dict[str, str] | None, str | None]:
    start = time.perf_counter()
    headers: dict[str, str] | None = None

    try:
        if is_socks_proxy(proxy):
            connector = ProxyConnector.from_url(proxy_connector_url(proxy))
            async with aiohttp.ClientSession(connector=connector) as sess:
                async with sess.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    body = await resp.text()
                    latency = (time.perf_counter() - start) * 1000
                    headers = {k: v for k, v in resp.headers.items()}
                    if resp.status != 200:
                        return False, latency, None, headers, f"HTTP {resp.status}"
                    return True, latency, extract_ip(body), headers, None
        else:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(
                    url,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    body = await resp.text()
                    latency = (time.perf_counter() - start) * 1000
                    headers = {k: v for k, v in resp.headers.items()}
                    if resp.status != 200:
                        return False, latency, None, headers, f"HTTP {resp.status}"
                    return True, latency, extract_ip(body), headers, None
    except Exception as exc:
        return False, (time.perf_counter() - start) * 1000, None, headers, str(exc)[:160]


async def validate_proxy(
    candidate: ProxyCandidate,
    sem: asyncio.Semaphore,
    direct_ip: str | None,
) -> ProxyResult:
    async with sem:
        result = ProxyResult(proxy=candidate.proxy, sources=sorted(candidate.sources))

        http_ok = False
        latency_ms: float | None = None
        exit_ip: str | None = None
        headers: dict[str, str] | None = None
        last_error: str | None = None

        for url in HTTP_TEST_URLS:
            ok, lat, ip, hdrs, err = await _request_via_proxy(candidate.proxy, url, VALIDATE_TIMEOUT)
            if ok and ip:
                http_ok = True
                latency_ms = round(lat, 1)
                exit_ip = ip
                headers = hdrs
                break
            last_error = err

        if not http_ok:
            result.error = last_error or "HTTP check failed"
            return result

        https_ok = False
        ok, _, ip, hdrs, _ = await _request_via_proxy(candidate.proxy, HTTPS_TEST_URL, VALIDATE_TIMEOUT)
        if ok:
            https_ok = True
            if ip:
                exit_ip = ip
            if hdrs:
                headers = hdrs

        anonymity = classify_anonymity(direct_ip, exit_ip, headers)
        if candidate.elite_hint and anonymity in {"anonymous", "elite"}:
            anonymity = "elite"

        result.ok = True
        result.http_ok = True
        result.https_ok = https_ok
        result.latency_ms = latency_ms
        result.exit_ip = exit_ip
        result.anonymity = anonymity
        result.score = compute_score(https_ok, latency_ms, anonymity)
        return result


async def validate_round(
    candidates: list[ProxyCandidate],
    direct_ip: str | None,
    round_num: int,
) -> list[ProxyResult]:
    sem = asyncio.Semaphore(MAX_CONCURRENT_VALIDATE)
    total = len(candidates)
    log(f"  Round {round_num}: validating {total} proxies ({MAX_CONCURRENT_VALIDATE} concurrent)...")

    completed = 0
    working = 0
    results: list[ProxyResult] = []

    async def run_one(candidate: ProxyCandidate) -> ProxyResult:
        nonlocal completed, working
        res = await validate_proxy(candidate, sem, direct_ip)
        completed += 1
        if res.ok:
            working += 1
            res.round_passed = round_num
        if completed % 50 == 0 or completed == total:
            log(f"    progress: {completed}/{total} checked, {working} working so far")
        return res

    tasks = [run_one(c) for c in candidates]
    results = await asyncio.gather(*tasks)
    survivors = [r for r in results if r.ok]
    log(f"  Round {round_num} done: {len(survivors)}/{total} passed")
    return survivors


# ---------------------------------------------------------------------------
# Aggregation & output
# ---------------------------------------------------------------------------

def merge_candidates(
    source_reports: list[SourceResult],
    fetched_batches: list[tuple[SourceResult, list[Any]]],
) -> dict[str, ProxyCandidate]:
    pool: dict[str, ProxyCandidate] = {}

    for report, items in fetched_batches:
        if not report.ok:
            continue
        for item in items:
            if isinstance(item, tuple):
                proxy, elite_hint = item
            else:
                proxy, elite_hint = str(item), False
            if "://" not in proxy:
                proxy = normalize_proxy(proxy)
            if not proxy:
                continue
            if proxy not in pool:
                pool[proxy] = ProxyCandidate(proxy=proxy)
            pool[proxy].sources.add(report.name)
            if elite_hint:
                pool[proxy].elite_hint = True

    return pool


def sort_results(results: list[ProxyResult]) -> list[ProxyResult]:
    return sorted(
        results,
        key=lambda r: (-r.score, r.latency_ms if r.latency_ms is not None else 99999),
    )


def result_to_dict(result: ProxyResult) -> dict[str, Any]:
    return asdict(result)


def write_outputs(
    all_working: list[ProxyResult],
    source_reports: list[SourceResult],
    stats: dict[str, Any],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sorted_working = sort_results(all_working)
    premium = [r for r in sorted_working if r.score >= 3 and (r.latency_ms or 99999) < 3000]

    working_json = OUTPUT_DIR / "working_proxies.json"
    premium_json = OUTPUT_DIR / "premium_proxies.json"
    working_txt = OUTPUT_DIR / "working_proxies.txt"
    report_md = OUTPUT_DIR / "hunt_report.md"

    working_json.write_text(
        json.dumps([result_to_dict(r) for r in sorted_working], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    premium_json.write_text(
        json.dumps([result_to_dict(r) for r in premium], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    working_txt.write_text("\n".join(r.proxy for r in sorted_working) + ("\n" if sorted_working else ""), encoding="utf-8")
    report_md.write_text(build_report_md(source_reports, sorted_working, premium, stats), encoding="utf-8")

    log("")
    log("Output files:")
    log(f"  {working_json}")
    log(f"  {premium_json}")
    log(f"  {working_txt}")
    log(f"  {report_md}")


def build_report_md(
    source_reports: list[SourceResult],
    working: list[ProxyResult],
    premium: list[ProxyResult],
    stats: dict[str, Any],
) -> str:
    lines = [
        "# Proxy Hunt Report",
        "",
        f"- **Started**: {stats['started_at']}",
        f"- **Finished**: {stats['finished_at']}",
        f"- **Duration**: {stats['duration_s']}s",
        f"- **Unique candidates**: {stats['unique_candidates']}",
        f"- **Round 1 survivors**: {stats['round1_survivors']}",
        f"- **Round 2 survivors (final)**: {stats['round2_survivors']}",
        f"- **Premium proxies (score>=3, latency<3000ms)**: {len(premium)}",
        "",
        "## Test Configuration",
        "",
        f"- HTTP test URLs: {', '.join(f'`{u}`' for u in HTTP_TEST_URLS)}",
        f"- HTTPS test URL: `{HTTPS_TEST_URL}`",
        f"- Timeout: {VALIDATE_TIMEOUT}s per proxy",
        f"- Concurrency: {MAX_CONCURRENT_VALIDATE}",
        f"- Direct IP: `{stats.get('direct_ip', 'unknown')}`",
        "",
        "## Scoring",
        "",
        "- `+2` HTTPS works",
        "- `+1` latency < 1000ms",
        "- `+1` latency < 3000ms",
        "- `+1` elite anonymity bonus",
        "",
        "## Source Fetch Summary",
        "",
        "| Source | Status | Fetched | Latency(ms) |",
        "|--------|--------|---------|-------------|",
    ]

    for src in source_reports:
        status = "OK" if src.ok else f"FAIL ({src.error})"
        fetched = src.fetched if src.ok else 0
        lat = src.latency_ms if src.latency_ms is not None else "N/A"
        lines.append(f"| {src.name} | {status} | {fetched} | {lat} |")

    lines.extend(["", "## Top Working Proxies", ""])
    if working:
        lines.append("| Proxy | Score | Latency(ms) | HTTPS | Anonymity | Exit IP | Sources |")
        lines.append("|-------|-------|-------------|-------|-----------|---------|---------|")
        for r in working[:30]:
            https = "yes" if r.https_ok else "no"
            lines.append(
                f"| `{r.proxy}` | {r.score} | {r.latency_ms} | {https} | {r.anonymity} | "
                f"{r.exit_ip or 'N/A'} | {', '.join(r.sources[:2])}{'...' if len(r.sources) > 2 else ''} |"
            )
    else:
        lines.append("_No working proxies found._")

    if premium:
        lines.extend(["", "## Premium Proxies", ""])
        for r in premium[:20]:
            lines.append(
                f"- `{r.proxy}` — score={r.score}, latency={r.latency_ms}ms, "
                f"https={r.https_ok}, anonymity={r.anonymity}"
            )

    latencies = [r.latency_ms for r in working if r.latency_ms is not None]
    if latencies:
        lines.extend([
            "",
            "## Latency Stats (working)",
            "",
            f"- Min: {min(latencies):.1f}ms",
            f"- Median: {statistics.median(latencies):.1f}ms",
            f"- Mean: {statistics.mean(latencies):.1f}ms",
            f"- Max: {max(latencies):.1f}ms",
        ])

    https_count = sum(1 for r in working if r.https_ok)
    elite_count = sum(1 for r in working if r.anonymity == "elite")
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Working HTTP: {len(working)}",
        f"- Working HTTPS: {https_count}",
        f"- Elite/anonymous: {elite_count} elite, "
        f"{sum(1 for r in working if r.anonymity == 'anonymous')} anonymous",
        "",
        "Free proxies decay quickly — re-run this hunt before production use.",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main hunt orchestration
# ---------------------------------------------------------------------------

Fetcher = Callable[[aiohttp.ClientSession], Coroutine[Any, Any, tuple[SourceResult, list[Any]]]]


async def fetch_all_sources(session: aiohttp.ClientSession) -> tuple[list[SourceResult], list[tuple[SourceResult, list[Any]]]]:
    fetchers: list[tuple[str, Fetcher]] = [
        ("Geonode", fetch_geonode),
        ("ProxyScrape HTTP", lambda s: fetch_proxyscrape(s, "http")),
        ("ProxyScrape HTTPS", lambda s: fetch_proxyscrape(s, "https")),
        ("ProxyScrape SOCKS5", lambda s: fetch_proxyscrape(s, "socks5")),
        ("OpenProxyList HTTP", lambda s: fetch_openproxylist(s, "http")),
        ("OpenProxyList SOCKS5", lambda s: fetch_openproxylist(s, "socks5")),
        ("proxifly HTTP", lambda s: fetch_proxifly(s, "http")),
        ("proxifly SOCKS5", lambda s: fetch_proxifly(s, "socks5")),
        ("iplocate", fetch_iplocate),
        (
            "TheSpeedX HTTP",
            lambda s: fetch_github_txt(
                s,
                "GitHub TheSpeedX (http)",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                "http",
            ),
        ),
        (
            "TheSpeedX SOCKS5",
            lambda s: fetch_github_txt(
                s,
                "GitHub TheSpeedX (socks5)",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
                "socks5",
            ),
        ),
        (
            "jetkai HTTP",
            lambda s: fetch_github_txt(
                s,
                "GitHub jetkai (http)",
                "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
                "http",
            ),
        ),
        (
            "jetkai SOCKS5",
            lambda s: fetch_github_txt(
                s,
                "GitHub jetkai (socks5)",
                "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
                "socks5",
            ),
        ),
        (
            "monosans HTTP",
            lambda s: fetch_github_txt(
                s,
                "GitHub monosans (http)",
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
                "http",
            ),
        ),
        (
            "monosans SOCKS5",
            lambda s: fetch_github_txt(
                s,
                "GitHub monosans (socks5)",
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
                "socks5",
            ),
        ),
        (
            "ShiftyTR HTTP",
            lambda s: fetch_github_txt(
                s,
                "GitHub ShiftyTR (http)",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
                "http",
            ),
        ),
        (
            "hookzof SOCKS5",
            lambda s: fetch_github_txt(
                s,
                "GitHub hookzof (socks5)",
                "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
                "socks5",
            ),
        ),
        ("free-proxy-list.net", fetch_free_proxy_list_net),
        ("pubproxy.com", fetch_pubproxy),
        ("proxy-list.download HTTP", lambda s: fetch_proxy_list_download(s, "http")),
        ("proxy-list.download HTTPS", lambda s: fetch_proxy_list_download(s, "https")),
        ("proxy-list.download SOCKS5", lambda s: fetch_proxy_list_download(s, "socks5")),
    ]

    reports: list[SourceResult] = []
    batches: list[tuple[SourceResult, list[Any]]] = []

    log(f"Fetching from {len(fetchers)} sources...")
    for label, fetcher in fetchers:
        log(f"  [{label}] fetching...", )
        try:
            report, proxies = await fetcher(session)
        except Exception as exc:
            report = SourceResult(name=label, url="(unknown)", error=str(exc)[:200])
            proxies = []
        reports.append(report)
        batches.append((report, proxies))
        if report.ok:
            log(f"    OK: {report.fetched} proxies ({report.latency_ms}ms)")
        else:
            log(f"    FAIL: {report.error}")

    return reports, batches


async def main() -> None:
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()

    log("=" * 70)
    log("PROXY HUNTER — high-quality free proxy discovery")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    headers = {"User-Agent": "ProxyHunter/1.0 (+https://github.com/local/proxy-test)"}

    async with aiohttp.ClientSession(headers=headers) as session:
        log("Detecting direct IP (for anonymity check)...")
        direct_ip = await get_direct_ip(session)
        log(f"  Direct IP: {direct_ip or 'unknown'}")

        source_reports, batches = await fetch_all_sources(session)
        pool = merge_candidates(source_reports, batches)
        candidates = list(pool.values())

        log("")
        log(f"Collected {len(candidates)} unique proxy candidates from {len(source_reports)} sources")

        if not candidates:
            log("No proxies to validate. Exiting.")
            stats = {
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_s": round(time.perf_counter() - started, 1),
                "unique_candidates": 0,
                "round1_survivors": 0,
                "round2_survivors": 0,
                "direct_ip": direct_ip,
            }
            write_outputs([], source_reports, stats)
            return

        round1 = await validate_round(candidates, direct_ip, round_num=1)
        round1_map = {r.proxy: pool[r.proxy] for r in round1}
        round2_candidates = [
            ProxyCandidate(
                proxy=r.proxy,
                sources=pool[r.proxy].sources,
                elite_hint=pool[r.proxy].elite_hint or r.anonymity == "elite",
            )
            for r in round1
        ]

        if round2_candidates:
            round2 = await validate_round(round2_candidates, direct_ip, round_num=2)
        else:
            round2 = []

        # Preserve source metadata on final results
        final: list[ProxyResult] = []
        for r in round2:
            r.sources = sorted(round1_map.get(r.proxy, pool.get(r.proxy, ProxyCandidate(r.proxy))).sources)
            r.round_passed = 2
            final.append(r)

    duration = round(time.perf_counter() - started, 1)
    finished_at = datetime.now(timezone.utc).isoformat()
    final_sorted = sort_results(final)
    premium = [r for r in final_sorted if r.score >= 3 and (r.latency_ms or 99999) < 3000]

    stats = {
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_s": duration,
        "unique_candidates": len(candidates),
        "round1_survivors": len(round1),
        "round2_survivors": len(final),
        "direct_ip": direct_ip,
    }

    write_outputs(final_sorted, source_reports, stats)

    log("")
    log("=" * 70)
    log("HUNT COMPLETE")
    log(f"  Candidates: {len(candidates)}")
    log(f"  Round 1 passed: {len(round1)}")
    log(f"  Round 2 passed: {len(final)}")
    log(f"  Premium (score>=3): {len(premium)}")
    log(f"  Duration: {duration}s")
    log("=" * 70)

    if final_sorted:
        log("")
        log("Top 10 proxies:")
        for i, r in enumerate(final_sorted[:10], 1):
            log(
                f"  {i}. {r.proxy} | score={r.score} | {r.latency_ms}ms | "
                f"https={r.https_ok} | {r.anonymity} | ip={r.exit_ip}"
            )


if __name__ == "__main__":
    asyncio.run(main())