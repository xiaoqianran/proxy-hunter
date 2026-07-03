# 各平台代理可用度排名（独立测试）

- **测试时间**: 2026-07-03 17:34:49 UTC
- **平台数量**: 39
- **模式**: standard
- **每平台抽样**: 最多 50 个
- **并发**: 80 | **超时**: 4.0s
- **验证端点**: icanhazip.com
- **总耗时**: 18.3s

## 排名（按成功率 → 可用数）

| 排名 | Source ID | 平台 | 协议 | 拉取 | 测试 | 可用 | 成功率 | HTTPS | 验证耗时 | 中位延迟 |
|------|-----------|------|------|------|------|------|--------|-------|----------|----------|
| 1 | `vakhov_http` | vakhov/fresh-proxy-list | HTTP | 524 | 50 | 28 | **56.0%** | 0 | 2010.9ms | 22.1 |
| 2 | `proxifly_http` | proxifly/free-proxy-list | HTTP | 1177 | 50 | 22 | **44.0%** | 2 | 4406.7ms | 26.1 |
| 3 | `iplocate_http` | iplocate/free-proxy-list | HTTP | 662 | 50 | 20 | **40.0%** | 3 | 4952.5ms | 463.9 |
| 4 | `proxyscrape_api_http` | ProxyScrape API v4 | HTTP Elite | 171 | 50 | 19 | **38.0%** | 8 | 5184.5ms | 653.7 |
| 5 | `monosans_http` | monosans/proxy-list | HTTP | 136 | 50 | 18 | **36.0%** | 15 | 4792.0ms | 508.6 |
| 6 | `ErcinDedeoglu_http` | ErcinDedeoglu/proxies | HTTP | 26723 | 50 | 17 | **34.0%** | 0 | 4968.9ms | 128.5 |
| 7 | `proxyscrape_api_socks5` | ProxyScrape API v4 | SOCKS5 Elite | 741 | 50 | 17 | **34.0%** | 8 | 3993.1ms | 970.8 |
| 8 | `databay_socks5` | databay-labs/free-proxy-list | SOCKS5 | 359 | 50 | 13 | **26.0%** | 6 | 5168.3ms | 1092.2 |
| 9 | `iplocate_socks5` | iplocate/free-proxy-list | SOCKS5 | 1239 | 50 | 12 | **24.0%** | 5 | 3146.7ms | 625.5 |
| 10 | `proxyscrape_api_socks4` | ProxyScrape API v4 | SOCKS4 Elite | 147 | 50 | 11 | **22.0%** | 2 | 4062.5ms | 526.6 |
| 11 | `hookzof_socks5` | hookzof/socks5_list | SOCKS5 | 486 | 50 | 11 | **22.0%** | 5 | 4392.7ms | 1502.1 |
| 12 | `vakhov_socks5` | vakhov/fresh-proxy-list | SOCKS5 | 21 | 21 | 4 | **19.0%** | 3 | 4262.9ms | 615.9 |
| 13 | `proxifly_all` | proxifly/free-proxy-list | ALL | 3700 | 50 | 8 | **16.0%** | 2 | 4363.3ms | 338.6 |
| 14 | `databay_http` | databay-labs/free-proxy-list | HTTP | 1849 | 50 | 7 | **14.0%** | 2 | 4553.0ms | 1785.0 |
| 15 | `TheSpeedX_http` | TheSpeedX/PROXY-List | HTTP | 2817 | 50 | 7 | **14.0%** | 1 | 4484.9ms | 2397.6 |
| 16 | `TheSpeedX_socks5` | TheSpeedX/PROXY-List | SOCKS5 | 2306 | 50 | 6 | **12.0%** | 1 | 2846.6ms | 175.8 |
| 17 | `vakhov_socks4` | vakhov/fresh-proxy-list | SOCKS4 | 165 | 50 | 6 | **12.0%** | 0 | 3519.3ms | 694.5 |
| 18 | `jetkai_socks4` | jetkai/proxy-list | SOCKS4 | 1603 | 50 | 5 | **10.0%** | 0 | 2508.5ms | 384.8 |
| 19 | `TheSpeedX_socks4` | TheSpeedX/PROXY-List | SOCKS4 | 2468 | 50 | 5 | **10.0%** | 0 | 2196.9ms | 507.9 |
| 20 | `jetkai_socks5` | jetkai/proxy-list | SOCKS5 | 405 | 50 | 4 | **8.0%** | 0 | 3659.8ms | 555.9 |
| 21 | `proxifly_socks5` | proxifly/free-proxy-list | SOCKS5 | 539 | 50 | 4 | **8.0%** | 2 | 3661.0ms | 620.0 |
| 22 | `ShiftyTR_http` | ShiftyTR/Proxy-List | HTTP | 40 | 40 | 3 | **7.5%** | 0 | 2512.5ms | 397.6 |
| 23 | `proxifly_socks4` | proxifly/free-proxy-list | SOCKS4 | 771 | 50 | 3 | **6.0%** | 0 | 3562.5ms | 496.5 |
| 24 | `proxylist_to_socks5` | proxylist-to/proxy-list | SOCKS5 | 196 | 50 | 2 | **4.0%** | 1 | 2012.2ms | 266.4 |
| 25 | `openproxylist_https` | roosterkid/openproxylist | HTTPS | 139 | 50 | 2 | **4.0%** | 0 | 4009.9ms | 508.7 |
| 26 | `proxylist_to_http` | proxylist-to/proxy-list | HTTP | 750 | 50 | 1 | **2.0%** | 0 | 4000.6ms | 143.8 |
| 27 | `proxylist_to_socks4` | proxylist-to/proxy-list | SOCKS4 | 261 | 50 | 1 | **2.0%** | 0 | 2948.6ms | 944.5 |
| 28 | `prxchk_http` | prxchk/proxy-list | HTTP | 58 | 50 | 1 | **2.0%** | 0 | 4714.5ms | 2709.1 |
| 29 | `jetkai_http` | jetkai/proxy-list | HTTP | 1801 | 50 | 0 | **0.0%** | 0 | 4010.0ms | — |
| 30 | `jetkai_https` | jetkai/proxy-list | HTTPS | 2161 | 50 | 0 | **0.0%** | 0 | 2008.9ms | — |
| 31 | `openproxylist_socks4` | roosterkid/openproxylist | SOCKS4 | 150 | 50 | 0 | **0.0%** | 0 | 2012.7ms | — |
| 32 | `openproxylist_socks5` | roosterkid/openproxylist | SOCKS5 | 10 | 10 | 0 | **0.0%** | 0 | 2004.9ms | — |
| 33 | `proxifly_https` | proxifly/free-proxy-list | HTTPS | 1103 | 50 | 0 | **0.0%** | 0 | 1870.3ms | — |
| 34 | `prxchk_socks4` | prxchk/proxy-list | SOCKS4 | 32 | 32 | 0 | **0.0%** | 0 | 2006.4ms | — |
| 35 | `prxchk_socks5` | prxchk/proxy-list | SOCKS5 | 10 | 10 | 0 | **0.0%** | 0 | 2003.5ms | — |
| 36 | `vakhov_https` | vakhov/fresh-proxy-list | HTTPS | 6 | 6 | 0 | **0.0%** | 0 | 2000.4ms | — |

## 拉取失败

- `mmpx12_http`: HTTP 404
- `monosans_http_anonymous`: HTTP 404
- `proxyscrape_mirror_http`: HTTP 404

## 分平台报告

每个平台独立结果见 `results/{source_id}.md`

- [ErcinDedeoglu_http](./ErcinDedeoglu_http.md) — ErcinDedeoglu/proxies / HTTP
- [ShiftyTR_http](./ShiftyTR_http.md) — ShiftyTR/Proxy-List / HTTP
- [TheSpeedX_http](./TheSpeedX_http.md) — TheSpeedX/PROXY-List / HTTP
- [TheSpeedX_socks4](./TheSpeedX_socks4.md) — TheSpeedX/PROXY-List / SOCKS4
- [TheSpeedX_socks5](./TheSpeedX_socks5.md) — TheSpeedX/PROXY-List / SOCKS5
- [databay_http](./databay_http.md) — databay-labs/free-proxy-list / HTTP
- [databay_socks5](./databay_socks5.md) — databay-labs/free-proxy-list / SOCKS5
- [hookzof_socks5](./hookzof_socks5.md) — hookzof/socks5_list / SOCKS5
- [iplocate_http](./iplocate_http.md) — iplocate/free-proxy-list / HTTP
- [iplocate_socks5](./iplocate_socks5.md) — iplocate/free-proxy-list / SOCKS5
- [jetkai_http](./jetkai_http.md) — jetkai/proxy-list / HTTP
- [jetkai_https](./jetkai_https.md) — jetkai/proxy-list / HTTPS
- [jetkai_socks4](./jetkai_socks4.md) — jetkai/proxy-list / SOCKS4
- [jetkai_socks5](./jetkai_socks5.md) — jetkai/proxy-list / SOCKS5
- [mmpx12_http](./mmpx12_http.md) — mmpx12/proxy-list / HTTP
- [monosans_http](./monosans_http.md) — monosans/proxy-list / HTTP
- [monosans_http_anonymous](./monosans_http_anonymous.md) — monosans/proxy-list / HTTP Anonymous
- [openproxylist_https](./openproxylist_https.md) — roosterkid/openproxylist / HTTPS
- [openproxylist_socks4](./openproxylist_socks4.md) — roosterkid/openproxylist / SOCKS4
- [openproxylist_socks5](./openproxylist_socks5.md) — roosterkid/openproxylist / SOCKS5
- [proxifly_all](./proxifly_all.md) — proxifly/free-proxy-list / ALL
- [proxifly_http](./proxifly_http.md) — proxifly/free-proxy-list / HTTP
- [proxifly_https](./proxifly_https.md) — proxifly/free-proxy-list / HTTPS
- [proxifly_socks4](./proxifly_socks4.md) — proxifly/free-proxy-list / SOCKS4
- [proxifly_socks5](./proxifly_socks5.md) — proxifly/free-proxy-list / SOCKS5
- [proxylist_to_http](./proxylist_to_http.md) — proxylist-to/proxy-list / HTTP
- [proxylist_to_socks4](./proxylist_to_socks4.md) — proxylist-to/proxy-list / SOCKS4
- [proxylist_to_socks5](./proxylist_to_socks5.md) — proxylist-to/proxy-list / SOCKS5
- [proxyscrape_api_http](./proxyscrape_api_http.md) — ProxyScrape API v4 / HTTP Elite
- [proxyscrape_api_socks4](./proxyscrape_api_socks4.md) — ProxyScrape API v4 / SOCKS4 Elite
- [proxyscrape_api_socks5](./proxyscrape_api_socks5.md) — ProxyScrape API v4 / SOCKS5 Elite
- [proxyscrape_mirror_http](./proxyscrape_mirror_http.md) — proxyscrape/free-proxy-list / HTTP Mirror
- [prxchk_http](./prxchk_http.md) — prxchk/proxy-list / HTTP
- [prxchk_socks4](./prxchk_socks4.md) — prxchk/proxy-list / SOCKS4
- [prxchk_socks5](./prxchk_socks5.md) — prxchk/proxy-list / SOCKS5
- [vakhov_http](./vakhov_http.md) — vakhov/fresh-proxy-list / HTTP
- [vakhov_https](./vakhov_https.md) — vakhov/fresh-proxy-list / HTTPS
- [vakhov_socks4](./vakhov_socks4.md) — vakhov/fresh-proxy-list / SOCKS4
- [vakhov_socks5](./vakhov_socks5.md) — vakhov/fresh-proxy-list / SOCKS5