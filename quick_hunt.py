#!/usr/bin/env python3
"""Quick proxy hunt: Geonode + monosans + jetkai, dual-round validation."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from aiohttp_socks import ProxyConnector

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(__file__).parent / "results"
VALIDATE_TIMEOUT = 8
MAX_CONCURRENT = 25
FETCH_TIMEOUT = 25
GEONODE_MAX_PAGES = 5

HTTP_TEST_URL = "http://icanhazip.com"
HTTPS_TEST_URL = "https://icanhazip.com"

IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IP_PORT_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+:\d+$")


@dataclass
class SourceResult:
    name: str
    url: str
    ok: bool = False
    error: str | None = None
    fetched: int = 0


@dataclass
class ProxyCandidate:
    proxy: str
    sources: set[str] = field(default_factory=set)


@dataclass
class ProxyResult:
    proxy: str
    ok: bool = False
    http_ok: bool = False
    https_ok: bool = False
    latency_ms: float | None = None
    exit_ip: str | None = None
    sources: list[str] = field(default_factory=list)
    error: str | None = None


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


def is_socks_proxy(proxy: str) -> bool:
    return proxy.startswith("socks4") or proxy.startswith("socks5")


def proxy_connector_url(proxy: str) -> str:
    if proxy.startswith("socks5h://"):
        return proxy
    if proxy.startswith("socks5://"):
        return "socks5h://" + proxy[len("socks5://") :]
    return proxy


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

async def fetch_text(session: aiohttp.ClientSession, url: str) -> tuple[str | None, str | None]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            if resp.status != 200:
                return None, f"HTTP {resp.status}"
            return await resp.text(), None
    except Exception as exc:
        return None, str(exc)[:200]


async def fetch_json(session: aiohttp.ClientSession, url: str) -> tuple[dict | None, str | None]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            if resp.status != 200:
                return None, f"HTTP {resp.status}"
            return await resp.json(), None
    except Exception as exc:
        return None, str(exc)[:200]


async def fetch_lines_source(
    session: aiohttp.ClientSession,
    name: str,
    url: str,
    scheme: str = "http",
) -> tuple[SourceResult, list[str]]:
    result = SourceResult(name=name, url=url)
    text, err = await fetch_text(session, url)
    if err:
        result.error = err
        return result, []
    proxies = parse_ip_port_lines(text, scheme)
    result.ok = True
    result.fetched = len(proxies)
    return result, proxies


async def fetch_geonode(session: aiohttp.ClientSession) -> tuple[SourceResult, list[str]]:
    name = "Geonode API (elite, google, uptime>=80, latency<=500)"
    base = (
        "https://proxylist.geonode.com/api/proxy-list"
        "?limit=100&sort_by=lastChecked&sort_type=desc"
        "&upTime=80&latency=500&anonymityLevel=elite&google=true"
    )
    result = SourceResult(name=name, url=base)
    proxies: list[str] = []
    seen: set[str] = set()
    pages_ok = 0

    for page in range(1, GEONODE_MAX_PAGES + 1):
        url = f"{base}&page={page}"
        payload, err = await fetch_json(session, url)
        if err:
            if page == 1:
                result.error = err
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
            proxies.append(proxy)

    if pages_ok == 0:
        return result, []

    result.ok = True
    result.fetched = len(proxies)
    return result, proxies


async def fetch_all_sources(session: aiohttp.ClientSession) -> tuple[list[SourceResult], list[tuple[SourceResult, list[str]]]]:
    fetchers = [
        ("Geonode", fetch_geonode),
        (
            "monosans HTTP",
            lambda s: fetch_lines_source(
                s,
                "GitHub monosans (http)",
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
                "http",
            ),
        ),
        (
            "monosans SOCKS5",
            lambda s: fetch_lines_source(
                s,
                "GitHub monosans (socks5)",
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
                "socks5",
            ),
        ),
        (
            "jetkai HTTP",
            lambda s: fetch_lines_source(
                s,
                "GitHub jetkai (http)",
                "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
                "http",
            ),
        ),
        (
            "jetkai SOCKS5",
            lambda s: fetch_lines_source(
                s,
                "GitHub jetkai (socks5)",
                "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
                "socks5",
            ),
        ),
    ]

    reports: list[SourceResult] = []
    batches: list[tuple[SourceResult, list[str]]] = []

    log(f"Fetching from {len(fetchers)} sources...")
    for label, fetcher in fetchers:
        log(f"  [{label}] fetching...")
        try:
            report, proxies = await fetcher(session)
        except Exception as exc:
            report = SourceResult(name=label, url="(unknown)", error=str(exc)[:200])
            proxies = []
        reports.append(report)
        batches.append((report, proxies))
        if report.ok:
            log(f"    OK: {report.fetched} proxies")
        else:
            log(f"    FAIL: {report.error}")

    return reports, batches


def merge_candidates(batches: list[tuple[SourceResult, list[str]]]) -> list[ProxyCandidate]:
    pool: dict[str, ProxyCandidate] = {}
    for report, items in batches:
        if not report.ok:
            continue
        for proxy in items:
            if proxy not in pool:
                pool[proxy] = ProxyCandidate(proxy=proxy)
            pool[proxy].sources.add(report.name)
    return list(pool.values())


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

async def _request_via_proxy(
    proxy: str,
    url: str,
    timeout: int,
) -> tuple[bool, float, str | None, str | None]:
    start = time.perf_counter()
    try:
        if is_socks_proxy(proxy):
            connector = ProxyConnector.from_url(proxy_connector_url(proxy))
            async with aiohttp.ClientSession(connector=connector) as sess:
                async with sess.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    body = await resp.text()
                    latency = (time.perf_counter() - start) * 1000
                    if resp.status != 200:
                        return False, latency, None, f"HTTP {resp.status}"
                    return True, latency, extract_ip(body), None
        else:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(
                    url,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    body = await resp.text()
                    latency = (time.perf_counter() - start) * 1000
                    if resp.status != 200:
                        return False, latency, None, f"HTTP {resp.status}"
                    return True, latency, extract_ip(body), None
    except Exception as exc:
        return False, (time.perf_counter() - start) * 1000, None, str(exc)[:160]


async def validate_proxy(candidate: ProxyCandidate, sem: asyncio.Semaphore) -> ProxyResult:
    async with sem:
        result = ProxyResult(proxy=candidate.proxy, sources=sorted(candidate.sources))

        ok, lat, exit_ip, err = await _request_via_proxy(candidate.proxy, HTTP_TEST_URL, VALIDATE_TIMEOUT)
        if not ok or not exit_ip:
            result.error = err or "HTTP check failed"
            return result

        https_ok = False
        ok_https, _, ip_https, _ = await _request_via_proxy(candidate.proxy, HTTPS_TEST_URL, VALIDATE_TIMEOUT)
        if ok_https:
            https_ok = True
            if ip_https:
                exit_ip = ip_https

        result.ok = True
        result.http_ok = True
        result.https_ok = https_ok
        result.latency_ms = round(lat, 1)
        result.exit_ip = exit_ip
        return result


async def validate_round(candidates: list[ProxyCandidate], round_num: int) -> list[ProxyResult]:
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    total = len(candidates)
    log(f"  Round {round_num}: validating {total} proxies ({MAX_CONCURRENT} concurrent, {VALIDATE_TIMEOUT}s timeout)...")

    completed = 0
    working = 0

    async def run_one(candidate: ProxyCandidate) -> ProxyResult:
        nonlocal completed, working
        res = await validate_proxy(candidate, sem)
        completed += 1
        if res.ok:
            working += 1
        if completed % 50 == 0 or completed == total:
            log(f"    progress: {completed}/{total} checked, {working} working so far")
        return res

    results = await asyncio.gather(*[run_one(c) for c in candidates])
    survivors = [r for r in results if r.ok]
    log(f"  Round {round_num} done: {len(survivors)}/{total} passed")
    return survivors


def sort_by_latency(results: list[ProxyResult]) -> list[ProxyResult]:
    return sorted(results, key=lambda r: r.latency_ms if r.latency_ms is not None else 99999)


def save_results(working: list[ProxyResult], meta: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sorted_working = sort_by_latency(working)

    payload = {
        "meta": meta,
        "proxies": [asdict(r) for r in sorted_working],
    }

    json_path = OUTPUT_DIR / "quick_working.json"
    txt_path = OUTPUT_DIR / "quick_working.txt"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(
        "\n".join(r.proxy for r in sorted_working) + ("\n" if sorted_working else ""),
        encoding="utf-8",
    )

    log("")
    log("Saved:")
    log(f"  {json_path}")
    log(f"  {txt_path}")


async def main() -> None:
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()

    log("=" * 60)
    log("QUICK PROXY HUNT")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Test URL: {HTTP_TEST_URL} | Timeout: {VALIDATE_TIMEOUT}s | Concurrency: {MAX_CONCURRENT}")
    log("=" * 60)

    headers = {"User-Agent": "QuickProxyHunt/1.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        reports, batches = await fetch_all_sources(session)
        candidates = merge_candidates(batches)

        log("")
        log(f"Collected {len(candidates)} unique proxy candidates")

        if not candidates:
            log("No proxies to validate.")
            save_results([], {"started_at": started_at, "working_count": 0})
            return

        round1 = await validate_round(candidates, round_num=1)
        round1_map = {c.proxy: c for c in candidates}

        round2_candidates = [
            ProxyCandidate(proxy=r.proxy, sources=round1_map[r.proxy].sources)
            for r in round1
        ]

        if round2_candidates:
            round2 = await validate_round(round2_candidates, round_num=2)
        else:
            round2 = []

        for r in round2:
            r.sources = sorted(round1_map.get(r.proxy, ProxyCandidate(r.proxy)).sources)

    duration = round(time.perf_counter() - started, 1)
    final = sort_by_latency(round2)

    meta = {
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": duration,
        "unique_candidates": len(candidates),
        "round1_survivors": len(round1),
        "round2_survivors": len(final),
        "test_url": HTTP_TEST_URL,
        "timeout_s": VALIDATE_TIMEOUT,
        "concurrency": MAX_CONCURRENT,
        "sources": [asdict(r) for r in reports],
    }

    save_results(final, meta)

    log("")
    log("=" * 60)
    log("SUMMARY")
    log(f"  Candidates fetched: {len(candidates)}")
    log(f"  Round 1 passed:     {len(round1)}")
    log(f"  Round 2 passed:     {len(final)}")
    log(f"  Duration:           {duration}s")
    log("")
    log(f"Working proxies: {len(final)}")

    if final:
        log("")
        log("Top 10 fastest:")
        for i, r in enumerate(final[:10], 1):
            https = "yes" if r.https_ok else "no"
            log(f"  {i:2}. {r.proxy}  —  {r.latency_ms}ms  HTTPS={https}  IP={r.exit_ip}")
    else:
        log("  (none)")

    log("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())