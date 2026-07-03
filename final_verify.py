#!/usr/bin/env python3
"""Final real-world verification of discovered proxies."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import aiohttp
from aiohttp_socks import ProxyConnector

RESULTS_DIR = Path(__file__).parent / "results"
CONCURRENCY = 15
TIMEOUT = 12

# Real targets crawlers actually hit
REAL_TARGETS = [
    ("icanhazip", "http://icanhazip.com"),
    ("https_icanhazip", "https://icanhazip.com"),
    ("moltbook_api", "https://www.moltbook.com/api/v1/agents?limit=1"),
    ("google", "https://www.google.com/"),
]


@dataclass
class RealWorldResult:
    proxy: str
    latency_ms: float | None
    https_ok: bool
    targets_ok: dict[str, bool]
    targets_status: dict[str, int | None]
    score: int
    exit_ip: str | None = None
    is_transparent: bool = False


async def test_proxy(proxy: str, direct_ip: str | None) -> RealWorldResult:
    is_socks = proxy.startswith("socks5")
    targets_ok: dict[str, bool] = {}
    targets_status: dict[str, int | None] = {}
    exit_ip = None
    latency = None
    https_ok = False

    try:
        if is_socks:
            connector = ProxyConnector.from_url(proxy)
            session_ctx = aiohttp.ClientSession(connector=connector)
        else:
            session_ctx = aiohttp.ClientSession()

        async with session_ctx as session:
            start = time.perf_counter()
            async with session.get(
                "http://icanhazip.com",
                proxy=None if is_socks else proxy,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
            ) as resp:
                latency = round((time.perf_counter() - start) * 1000, 1)
                if resp.status == 200:
                    exit_ip = (await resp.text()).strip()

            for name, url in REAL_TARGETS:
                try:
                    async with session.get(
                        url,
                        proxy=None if is_socks else proxy,
                        timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                        allow_redirects=True,
                    ) as resp:
                        targets_status[name] = resp.status
                        if name == "https_icanhazip":
                            https_ok = resp.status == 200
                        targets_ok[name] = resp.status in (200, 301, 302)
                except Exception:
                    targets_status[name] = None
                    targets_ok[name] = False
    except Exception:
        return RealWorldResult(
            proxy=proxy, latency_ms=None, https_ok=False,
            targets_ok={}, targets_status={}, score=0,
        )

    transparent = bool(direct_ip and exit_ip and direct_ip in exit_ip)
    score = sum(targets_ok.values())
    if https_ok:
        score += 2
    if latency and latency < 500:
        score += 2
    elif latency and latency < 1500:
        score += 1
    if not transparent:
        score += 1

    return RealWorldResult(
        proxy=proxy,
        latency_ms=latency,
        https_ok=https_ok,
        targets_ok=targets_ok,
        targets_status=targets_status,
        score=score,
        exit_ip=exit_ip,
        is_transparent=transparent,
    )


async def get_direct_ip() -> str | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("http://icanhazip.com", timeout=aiohttp.ClientTimeout(total=8)) as r:
                return (await r.text()).strip()
    except Exception:
        return None


async def main():
    # Collect proxies from all result files
    proxies: set[str] = set()

    for fname in ["quick_working.json", "working_proxies.json"]:
        path = RESULTS_DIR / fname
        if path.exists():
            data = json.loads(path.read_text())
            for p in data.get("proxies", data if isinstance(data, list) else []):
                if isinstance(p, dict):
                    proxies.add(p["proxy"])
                elif isinstance(p, str):
                    proxies.add(p)

    txt = RESULTS_DIR / "working_proxies.txt"
    if txt.exists():
        for line in txt.read_text().splitlines():
            line = line.strip()
            if line:
                proxies.add(line)

    # Always include Tor
    proxies.add("socks5://127.0.0.1:9050")

    direct_ip = await get_direct_ip()
    print(f"Direct IP: {direct_ip}")
    print(f"Verifying {len(proxies)} proxies against real targets...\n", flush=True)

    sem = asyncio.Semaphore(CONCURRENCY)

    async def run(p: str) -> RealWorldResult:
        async with sem:
            return await test_proxy(p, direct_ip)

    results = await asyncio.gather(*[run(p) for p in proxies])
    working = [r for r in results if r.targets_ok.get("icanhazip")]
    working.sort(key=lambda x: (-x.score, x.latency_ms or 99999))

    premium = [r for r in working if r.score >= 5 and not r.is_transparent]

    out = {
        "verified_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "direct_ip": direct_ip,
        "total_tested": len(proxies),
        "working": len(working),
        "premium": len(premium),
        "proxies": [asdict(r) for r in working],
        "premium_proxies": [asdict(r) for r in premium],
    }

    (RESULTS_DIR / "final_verified.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / "final_premium.txt").write_text(
        "\n".join(r.proxy for r in premium) + ("\n" if premium else ""),
        encoding="utf-8",
    )

    # Markdown report
    lines = [
        "# 最终可用高质量代理报告",
        "",
        f"- 验证时间: {out['verified_at']}",
        f"- 测试数量: {out['total_tested']}",
        f"- 可用: **{out['working']}**",
        f"- 优质 (score≥5, 非透明): **{out['premium']}**",
        "",
        "## 优质代理 TOP 列表",
        "",
        "| # | 代理 | 延迟 | HTTPS | Moltbook | Google | 匿名 | 评分 |",
        "|---|------|------|-------|----------|--------|------|------|",
    ]
    for i, r in enumerate(premium[:20], 1):
        anon = "透明" if r.is_transparent else "匿名"
        lines.append(
            f"| {i} | `{r.proxy}` | {r.latency_ms}ms | "
            f"{'✓' if r.https_ok else '✗'} | "
            f"{'✓' if r.targets_ok.get('moltbook_api') else '✗'} | "
            f"{'✓' if r.targets_ok.get('google') else '✗'} | "
            f"{anon} | {r.score} |"
        )

    lines.extend(["", "## 全部可用代理", ""])
    for r in working:
        lines.append(
            f"- `{r.proxy}` — {r.latency_ms}ms, score={r.score}, "
            f"ip={r.exit_ip}, https={'✓' if r.https_ok else '✗'}"
        )

    (RESULTS_DIR / "FINAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Working: {len(working)} | Premium: {len(premium)}\n")
    print("TOP Premium:")
    for i, r in enumerate(premium[:15], 1):
        print(
            f"  {i}. {r.proxy} | {r.latency_ms}ms | score={r.score} | "
            f"https={r.https_ok} | moltbook={r.targets_ok.get('moltbook_api')} | "
            f"anon={'透明' if r.is_transparent else 'OK'}"
        )
    print(f"\nSaved: {RESULTS_DIR / 'FINAL_REPORT.md'}")


if __name__ == "__main__":
    asyncio.run(main())