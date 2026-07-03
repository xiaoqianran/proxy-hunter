# Proxy Hunter

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Hunt, validate, and rank free proxies from 20+ sources.**

An async Python toolkit that fetches proxies from public APIs and GitHub lists, validates them against real endpoints (not httpbin), runs multi-round filtering, and outputs ready-to-use proxy lists for web scraping.

[中文文档](README_ZH.md)

---

## Why this project?

Most free-proxy tutorials fail because they test against **httpbin.org**, which blocks proxy traffic and makes every source look useless (~5% success). Proxy Hunter uses **icanhazip.com** and real targets (Google, custom APIs) instead.

In our benchmark (2026-07-03):

| Metric | Result |
|--------|--------|
| Candidates scanned | 11,000+ |
| Working proxies found | **77** |
| Premium (HTTPS, <3s) | **11** |
| Moltbook API verified | **8** |

---

## Features

- **20+ sources** — Geonode API (filtered), ProxyScrape, OpenProxyList, GitHub lists (proxifly, jetkai, monosans, iplocate…)
- **Async validation** — `aiohttp` + `aiohttp-socks`, 25–30 concurrent checks
- **Multi-round filtering** — survivors are re-tested to reduce false positives
- **Quality scoring** — HTTPS support, latency tiers, anonymity hints
- **Real-world verification** — optional checks against Google and your target API
- **Per-channel reports** — Markdown reports for each source under `results/channels/`
- **Tor support** — local SOCKS5 via `127.0.0.1:9050`

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/xiaoqianran/proxy-hunter.git
cd proxy-hunter

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Hunt proxies (recommended)

```bash
# Deep hunt — Geonode filters + curated lists (~8 min)
python geonode_hunt.py

# Quick hunt — smaller source set (~8 min)
python quick_hunt.py
```

### 3. Use the results

```bash
# Best proxies verified for HTTPS + target APIs
cat results/BEST_FOR_CRAWLING.txt
```

### 4. Real-world verification (optional)

```bash
python final_verify.py
```

### 5. Regenerate channel reports

```bash
python generate_channel_reports.py
```

---

## Usage in code

### HTTP proxy (aiohttp)

```python
import aiohttp

PROXY = "http://43.133.15.47:3128"

async with aiohttp.ClientSession() as session:
    async with session.get("https://example.com", proxy=PROXY) as resp:
        print(await resp.text())
```

### SOCKS5 proxy

```python
from aiohttp_socks import ProxyConnector

connector = ProxyConnector.from_url("socks5://193.25.215.182:22222")
async with aiohttp.ClientSession(connector=connector) as session:
    async with session.get("https://example.com") as resp:
        ...
```

### Proxy rotation

```python
proxies = open("results/BEST_FOR_CRAWLING.txt").read().splitlines()
proxy = proxies[request_count % len(proxies)]
```

### Tor

```bash
sudo apt install tor && sudo systemctl start tor
# SOCKS5: socks5://127.0.0.1:9050
```

---

## Project structure

```
proxy-hunter/
├── geonode_hunt.py              # Recommended: deep hunt
├── quick_hunt.py                # Fast hunt
├── final_verify.py              # Real-site verification
├── generate_channel_reports.py  # Build per-source .md reports
├── requirements.txt
├── _deprecated/                 # Archived failed experiments
└── results/
    ├── BEST_FOR_CRAWLING.txt    # Top proxies for scraping
    ├── ALL_WORKING.json         # All validated proxies
    ├── ALL_PREMIUM.txt          # HTTPS premium list
    ├── FINAL_REPORT.md          # Summary report
    └── channels/                # Per-source markdown reports
        └── 00-总览.md           # Index (Chinese)
```

---

## Scripts

| Script | Purpose | Runtime |
|--------|---------|---------|
| `geonode_hunt.py` | Geonode elite filters + monosans/jetkai/ShiftyTR | ~8 min |
| `quick_hunt.py` | Geonode + monosans + jetkai, 2-round validate | ~8 min |
| `final_verify.py` | Test proxies against Google & custom APIs | ~1 min |
| `generate_channel_reports.py` | Generate `results/channels/*.md` from JSON | <1 sec |

Archived scripts (`test_proxies.py`, `proxy_hunter.py`) are in `_deprecated/` — see `_deprecated/README.md`.

---

## Best sources (benchmark)

| Source | Strategy | Quality |
|--------|----------|---------|
| Geonode API | `elite` + `google=true` + `upTime≥80%` | Best metadata |
| monosans/proxy-list | Small curated GitHub list | Best HTTPS yield |
| jetkai/proxy-list | Large online list | High volume, needs filtering |
| Tor (local) | `apt install tor` | 100% up, slower (~1s) |

---

## Important notes

1. **Do not use httpbin.org** to test proxies — it returns 502/503 for proxy traffic.
2. **Free proxies decay fast** — re-run `geonode_hunt.py` before each crawl session.
3. **Transparent proxies leak your IP** — filtered out when possible; always verify exit IP.
4. **Rate limit** your scraper even with proxies (1–2 req/s is safe for most APIs).

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contributing

Issues and PRs welcome. If you find a reliable free proxy API, open an issue with the endpoint URL.