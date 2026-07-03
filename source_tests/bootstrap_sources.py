#!/usr/bin/env python3
"""Generate one JSON config file per proxy source platform."""

import json
from pathlib import Path

SOURCES_DIR = Path(__file__).parent / "sources"

# Each entry → sources/{id}.json
SOURCES = [
    # --- monosans ---
    ("monosans_http", "monosans/proxy-list", "HTTP", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", "http", "txt", "每小时", ""),
    ("monosans_http_anonymous", "monosans/proxy-list", "HTTP Anonymous", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt", "http", "txt", "每小时", "匿名分组"),
    # --- ShiftyTR ---
    ("ShiftyTR_http", "ShiftyTR/Proxy-List", "HTTP", "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt", "http", "txt", "不定期", ""),
    # --- jetkai ---
    ("jetkai_http", "jetkai/proxy-list", "HTTP", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt", "http", "txt", "每小时", ""),
    ("jetkai_https", "jetkai/proxy-list", "HTTPS", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt", "http", "txt", "每小时", "HTTPS 隧道列表"),
    ("jetkai_socks4", "jetkai/proxy-list", "SOCKS4", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt", "socks4", "txt", "每小时", ""),
    ("jetkai_socks5", "jetkai/proxy-list", "SOCKS5", "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt", "socks5", "txt", "每小时", ""),
    # --- Proxifly (CDN) ---
    ("proxifly_all", "proxifly/free-proxy-list", "ALL", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.txt", "http", "txt", "每5分钟", "CDN 最优入口"),
    ("proxifly_http", "proxifly/free-proxy-list", "HTTP", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt", "http", "txt", "每5分钟", ""),
    ("proxifly_https", "proxifly/free-proxy-list", "HTTPS", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/https/data.txt", "http", "txt", "每5分钟", ""),
    ("proxifly_socks4", "proxifly/free-proxy-list", "SOCKS4", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks4/data.txt", "socks4", "txt", "每5分钟", ""),
    ("proxifly_socks5", "proxifly/free-proxy-list", "SOCKS5", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt", "socks5", "txt", "每5分钟", ""),
    # --- ProxyScrape API v4 ---
    ("proxyscrape_api_http", "ProxyScrape API v4", "HTTP Elite", "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=http&timeout=5000&anonymity=elite", "http", "txt", "实时", "API 可过滤"),
    ("proxyscrape_api_socks4", "ProxyScrape API v4", "SOCKS4 Elite", "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=socks4&timeout=5000&anonymity=elite", "socks4", "txt", "实时", ""),
    ("proxyscrape_api_socks5", "ProxyScrape API v4", "SOCKS5 Elite", "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=5000&anonymity=elite", "socks5", "txt", "实时", ""),
    # --- ProxyScrape GitHub mirror ---
    ("proxyscrape_mirror_http", "proxyscrape/free-proxy-list", "HTTP Mirror", "https://raw.githubusercontent.com/proxyscrape/free-proxy-list/main/proxies/http.txt", "http", "txt", "定期", "GitHub mirror"),
    # --- vakhov/fresh-proxy-list ---
    ("vakhov_http", "vakhov/fresh-proxy-list", "HTTP", "https://vakhov.github.io/fresh-proxy-list/http.txt", "http", "txt", "持续更新", ""),
    ("vakhov_https", "vakhov/fresh-proxy-list", "HTTPS", "https://vakhov.github.io/fresh-proxy-list/https.txt", "http", "txt", "持续更新", ""),
    ("vakhov_socks4", "vakhov/fresh-proxy-list", "SOCKS4", "https://vakhov.github.io/fresh-proxy-list/socks4.txt", "socks4", "txt", "持续更新", ""),
    ("vakhov_socks5", "vakhov/fresh-proxy-list", "SOCKS5", "https://vakhov.github.io/fresh-proxy-list/socks5.txt", "socks5", "txt", "持续更新", ""),
    # --- TheSpeedX ---
    ("TheSpeedX_http", "TheSpeedX/PROXY-List", "HTTP", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", "http", "txt", "每日", "体量大"),
    ("TheSpeedX_socks4", "TheSpeedX/PROXY-List", "SOCKS4", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt", "socks4", "txt", "每日", ""),
    ("TheSpeedX_socks5", "TheSpeedX/PROXY-List", "SOCKS5", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt", "socks5", "txt", "每日", ""),
    # --- roosterkid/openproxylist ---
    ("openproxylist_https", "roosterkid/openproxylist", "HTTPS", "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt", "http", "txt", "每分钟", ""),
    ("openproxylist_socks4", "roosterkid/openproxylist", "SOCKS4", "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt", "socks4", "txt", "每分钟", ""),
    ("openproxylist_socks5", "roosterkid/openproxylist", "SOCKS5", "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt", "socks5", "txt", "每分钟", ""),
    # --- databay-labs ---
    ("databay_http", "databay-labs/free-proxy-list", "HTTP", "https://raw.githubusercontent.com/databay-labs/free-proxy-list/master/http.txt", "http", "txt", "每5分钟", "零MITM/严格SSL"),
    ("databay_socks5", "databay-labs/free-proxy-list", "SOCKS5", "https://raw.githubusercontent.com/databay-labs/free-proxy-list/master/socks5.txt", "socks5", "txt", "每5分钟", ""),
    # --- iplocate ---
    ("iplocate_http", "iplocate/free-proxy-list", "HTTP", "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/http.txt", "http", "txt", "每30分钟", ""),
    ("iplocate_socks5", "iplocate/free-proxy-list", "SOCKS5", "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/socks5.txt", "socks5", "txt", "每30分钟", ""),
    # --- prxchk ---
    ("prxchk_http", "prxchk/proxy-list", "HTTP", "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt", "http", "txt", "不定期", "补充源"),
    ("prxchk_socks4", "prxchk/proxy-list", "SOCKS4", "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks4.txt", "socks4", "txt", "不定期", ""),
    ("prxchk_socks5", "prxchk/proxy-list", "SOCKS5", "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt", "socks5", "txt", "不定期", ""),
    # --- proxylist-to ---
    ("proxylist_to_http", "proxylist-to/proxy-list", "HTTP", "https://raw.githubusercontent.com/proxylist-to/proxy-list/main/http.txt", "http", "txt", "不定期", "补充源"),
    ("proxylist_to_socks4", "proxylist-to/proxy-list", "SOCKS4", "https://raw.githubusercontent.com/proxylist-to/proxy-list/main/socks4.txt", "socks4", "txt", "不定期", ""),
    ("proxylist_to_socks5", "proxylist-to/proxy-list", "SOCKS5", "https://raw.githubusercontent.com/proxylist-to/proxy-list/main/socks5.txt", "socks5", "txt", "不定期", ""),
    # --- hookzof ---
    ("hookzof_socks5", "hookzof/socks5_list", "SOCKS5", "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt", "socks5", "txt", "不定期", "仅 SOCKS5"),
    # --- mmpx12 ---
    ("mmpx12_http", "mmpx12/proxy-list", "HTTP", "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt", "http", "txt", "不定期", "高质量备选"),
    # --- ErcinDedeoglu ---
    ("ErcinDedeoglu_http", "ErcinDedeoglu/proxies", "HTTP", "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt", "http", "txt", "不定期", "高质量备选"),
]


def main():
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    for row in SOURCES:
        sid, platform, proto, url, scheme, fmt, freq, notes = row
        cfg = {
            "id": sid,
            "platform": platform,
            "protocol_label": proto,
            "url": url,
            "scheme": scheme,
            "format": fmt,
            "update_frequency": freq,
            "notes": notes,
            "max_test": 50,
        }
        path = SOURCES_DIR / f"{sid}.json"
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  {path.name}")
    print(f"\nGenerated {len(SOURCES)} source configs.")


if __name__ == "__main__":
    main()