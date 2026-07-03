#!/usr/bin/env python3
"""Deep hunt: Geonode filtered + curated lists, merge with prior results."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import aiohttp
from aiohttp_socks import ProxyConnector

OUT = Path(__file__).parent / "results"
TIMEOUT = 8
CONCURRENCY = 25

GEONODE_URLS = [
    "https://proxylist.geonode.com/api/proxy-list?limit=100&page={p}&sort_by=speed&sort_type=asc&protocols=http&filterUpTime=90&upTime=90&filterLatency=500&latency=500&anonymityLevel=elite&google=true",
    "https://proxylist.geonode.com/api/proxy-list?limit=100&page={p}&sort_by=latency&sort_type=asc&protocols=http,socks5&filterUpTime=80&upTime=80&filterLatency=300&latency=300&anonymityLevel=elite",
    "https://proxylist.geonode.com/api/proxy-list?limit=100&page={p}&sort_by=lastChecked&sort_type=desc&protocols=http&anonymityLevel=elite&google=true",
]
CURATED = [
    ("monosans", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", "http"),
    ("ShiftyTR", "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt", "http"),
    ("jetkai", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt", "http"),
]
TEST_HTTP = "http://icanhazip.com"
TEST_HTTPS = "https://icanhazip.com"


@dataclass
class P:
    proxy: str
    latency_ms: float
    https_ok: bool
    exit_ip: str
    source: str


async def fetch_geonode(session: aiohttp.ClientSession) -> list[tuple[str, str]]:
    out = []
    for tpl in GEONODE_URLS:
        for page in range(1, 6):
            url = tpl.format(p=page)
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status != 200:
                        continue
                    data = await r.json()
                    for item in data.get("data", []):
                        proto = item.get("protocols", ["http"])[0]
                        out.append((f"{proto}://{item['ip']}:{item['port']}", "geonode"))
            except Exception:
                pass
    return out


async def fetch_txt(session: aiohttp.ClientSession, name: str, url: str, scheme: str) -> list[tuple[str, str]]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
            text = await r.text()
            return [(f"{scheme}://{ln.strip()}", name) for ln in text.splitlines() if ":" in ln.strip()]
    except Exception:
        return []


async def test_one(proxy: str, source: str) -> P | None:
    is_socks = proxy.startswith("socks5")
    try:
        if is_socks:
            conn = ProxyConnector.from_url(proxy)
            ctx = aiohttp.ClientSession(connector=conn)
        else:
            ctx = aiohttp.ClientSession()
        async with ctx as s:
            t0 = time.perf_counter()
            async with s.get(TEST_HTTP, proxy=None if is_socks else proxy,
                             timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                if r.status != 200:
                    return None
                ip = (await r.text()).strip()[:40]
                lat = round((time.perf_counter() - t0) * 1000, 1)
            https_ok = False
            try:
                async with s.get(TEST_HTTPS, proxy=None if is_socks else proxy,
                                 timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r2:
                    https_ok = r2.status == 200
            except Exception:
                pass
            return P(proxy, lat, https_ok, ip, source)
    except Exception:
        return None


async def main():
    # Load existing
    existing: set[str] = set()
    for f in ["quick_working.json", "final_verified.json"]:
        p = OUT / f
        if p.exists():
            d = json.loads(p.read_text())
            for item in d.get("proxies", d.get("premium_proxies", [])):
                if isinstance(item, dict):
                    existing.add(item.get("proxy", ""))

    async with aiohttp.ClientSession() as session:
        candidates: dict[str, str] = {}
        for proxy, src in await fetch_geonode(session):
            candidates[proxy] = src
        for name, url, scheme in CURATED:
            for proxy, src in await fetch_txt(session, name, url, scheme):
                candidates[proxy] = src

        # Tor
        candidates["socks5://127.0.0.1:9050"] = "tor"

        to_test = [(p, s) for p, s in candidates.items() if p not in existing]
        print(f"Candidates: {len(candidates)}, new to test: {len(to_test)}", flush=True)

        sem = asyncio.Semaphore(CONCURRENCY)

        async def run(item):
            async with sem:
                return await test_one(*item)

        found = [r for r in await asyncio.gather(*[run(i) for i in to_test]) if r]
        found.sort(key=lambda x: (not x.https_ok, x.latency_ms))

    # Merge with quick_working
    all_proxies: list[dict] = []
    qw = OUT / "quick_working.json"
    if qw.exists():
        all_proxies.extend(json.loads(qw.read_text()).get("proxies", []))

    seen = {p["proxy"] for p in all_proxies}
    for f in found:
        if f.proxy not in seen:
            all_proxies.append(asdict(f) | {"ok": True, "http_ok": True})
            seen.add(f.proxy)

    all_proxies.sort(key=lambda x: (not x.get("https_ok"), x.get("latency_ms", 9999)))

    premium = [p for p in all_proxies if p.get("https_ok") and (p.get("latency_ms") or 9999) < 3000]

    result = {
        "hunted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(all_proxies),
        "premium_count": len(premium),
        "new_found": len(found),
        "proxies": all_proxies,
        "premium": premium,
    }
    (OUT / "ALL_WORKING.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (OUT / "ALL_PREMIUM.txt").write_text("\n".join(p["proxy"] for p in premium) + "\n")

    print(f"\nTotal working: {len(all_proxies)} | Premium (HTTPS<3s): {len(premium)} | New: {len(found)}")
    print("\n=== PREMIUM PROXIES ===")
    for i, p in enumerate(premium, 1):
        print(f"  {i}. {p['proxy']}  {p.get('latency_ms')}ms  ip={p.get('exit_ip','?')}")


if __name__ == "__main__":
    asyncio.run(main())