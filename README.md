# Proxy Hunter

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Per-source free proxy testing toolkit** — fetch, validate, and rank proxies from 39 public platforms independently.

[中文文档](README_ZH.md)

---

## Why this project?

Most free-proxy tutorials test against **httpbin.org**, which blocks proxy traffic and makes every source look useless. Proxy Hunter validates each platform separately using **icanhazip.com**, so you can compare real availability per source.

Latest benchmark (2026-07-03, 39 platforms):

| Top source | Protocol | Success rate |
|------------|----------|--------------|
| vakhov/fresh-proxy-list | SOCKS4 | **86%** |
| ProxyScrape API v4 | HTTP Elite | **68%** |
| ProxyScrape API v4 | SOCKS5 Elite | **58%** |
| vakhov/fresh-proxy-list | HTTP | **56%** |
| Proxifly CDN | HTTP | **42%** |

Full ranking: [`source_tests/results/00_RANKING.md`](source_tests/results/00_RANKING.md)

---

## Quick Start

```bash
git clone https://github.com/xiaoqianran/proxy-hunter.git
cd proxy-hunter

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd source_tests
python bootstrap_sources.py   # generate 39 platform configs
python run_one.py proxifly_http  # test one platform (~1 min)
python run_all.py              # test all 39 (~10 min)
```

---

## Project structure

```
proxy-hunter/
├── source_tests/
│   ├── bootstrap_sources.py  # Generate sources/*.json
│   ├── run_one.py            # Test single platform
│   ├── run_all.py            # Test all platforms (isolated)
│   ├── sources/              # One JSON config per platform (39)
│   └── results/              # One .md + .json per platform
│       └── 00_RANKING.md     # Cross-platform ranking
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Usage in code

```python
import aiohttp

# Use proxies from source_tests/results/{platform}.json
PROXY = "http://43.133.15.47:3128"

async with aiohttp.ClientSession() as session:
    async with session.get("https://example.com", proxy=PROXY) as resp:
        print(await resp.text())
```

---

## Test rules

- Endpoint: `icanhazip.com` (not httpbin)
- Per platform: up to **50** random samples when list is larger
- 25 concurrent, 8s timeout
- HTTP pass → then HTTPS check

---

## License

MIT — see [LICENSE](LICENSE).