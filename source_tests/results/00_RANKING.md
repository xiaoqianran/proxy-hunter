# 各平台代理可用度排名（独立测试）

- **测试时间**: 2026-07-03 17:37:15 UTC
- **平台数量**: 39
- **模式**: standard
- **每平台抽样**: 最多 50 个
- **并发**: 80 | **超时**: 4.0s
- **验证端点**: icanhazip.com
- **总耗时**: 17.1s

## 排名（按成功率 → 可用数）

| 排名 | Source ID | 平台 | 协议 | 拉取 | 测试 | 可用 | 成功率 | HTTPS | 验证耗时 | 中位延迟 |
|------|-----------|------|------|------|------|------|--------|-------|----------|----------|
| 1 | `vakhov_http` | vakhov/fresh-proxy-list | HTTP | 524 | 50 | 35 | **70.0%** | 0 | 4021.9ms | 19.6 |
| 2 | `monosans_http` | monosans/proxy-list | HTTP | 136 | 50 | 23 | **46.0%** | 17 | 5225.1ms | 389.0 |
| 3 | `proxyscrape_api_http` | ProxyScrape API v4 | HTTP Elite | 171 | 50 | 23 | **46.0%** | 8 | 5795.3ms | 683.2 |
| 4 | `proxifly_http` | proxifly/free-proxy-list | HTTP | 1177 | 50 | 22 | **44.0%** | 3 | 5388.1ms | 23.9 |
| 5 | `ErcinDedeoglu_http` | ErcinDedeoglu/proxies | HTTP | 26723 | 50 | 14 | **28.0%** | 0 | 4508.1ms | 107.8 |
| 6 | `iplocate_http` | iplocate/free-proxy-list | HTTP | 662 | 50 | 12 | **24.0%** | 6 | 4668.0ms | 501.0 |
| 7 | `databay_socks5` | databay-labs/free-proxy-list | SOCKS5 | 359 | 50 | 11 | **22.0%** | 10 | 4088.6ms | 634.4 |
| 8 | `proxyscrape_api_socks5` | ProxyScrape API v4 | SOCKS5 Elite | 741 | 50 | 10 | **20.0%** | 4 | 3530.1ms | 670.9 |
| 9 | `iplocate_socks5` | iplocate/free-proxy-list | SOCKS5 | 1239 | 50 | 10 | **20.0%** | 8 | 3579.9ms | 949.4 |
| 10 | `proxyscrape_api_socks4` | ProxyScrape API v4 | SOCKS4 Elite | 147 | 50 | 8 | **16.0%** | 1 | 4807.1ms | 501.9 |
| 11 | `TheSpeedX_http` | TheSpeedX/PROXY-List | HTTP | 2817 | 50 | 8 | **16.0%** | 3 | 4770.4ms | 952.3 |
| 12 | `vakhov_socks5` | vakhov/fresh-proxy-list | SOCKS5 | 21 | 21 | 3 | **14.3%** | 3 | 2700.3ms | 601.3 |
| 13 | `proxifly_all` | proxifly/free-proxy-list | ALL | 3700 | 50 | 7 | **14.0%** | 2 | 4005.1ms | 320.1 |
| 14 | `vakhov_socks4` | vakhov/fresh-proxy-list | SOCKS4 | 165 | 50 | 7 | **14.0%** | 0 | 2526.7ms | 506.1 |
| 15 | `databay_http` | databay-labs/free-proxy-list | HTTP | 1849 | 50 | 6 | **12.0%** | 2 | 5704.8ms | 1787.2 |
| 16 | `proxifly_socks5` | proxifly/free-proxy-list | SOCKS5 | 539 | 50 | 5 | **10.0%** | 3 | 2611.6ms | 622.1 |
| 17 | `hookzof_socks5` | hookzof/socks5_list | SOCKS5 | 486 | 50 | 5 | **10.0%** | 2 | 4120.4ms | 950.9 |
| 18 | `openproxylist_https` | roosterkid/openproxylist | HTTPS | 139 | 50 | 4 | **8.0%** | 0 | 5630.3ms | 1894.4 |
| 19 | `ShiftyTR_http` | ShiftyTR/Proxy-List | HTTP | 40 | 40 | 3 | **7.5%** | 0 | 2107.2ms | 332.9 |
| 20 | `proxifly_socks4` | proxifly/free-proxy-list | SOCKS4 | 771 | 50 | 3 | **6.0%** | 0 | 2537.0ms | 388.8 |
| 21 | `jetkai_socks5` | jetkai/proxy-list | SOCKS5 | 405 | 50 | 3 | **6.0%** | 0 | 3656.0ms | 620.7 |
| 22 | `TheSpeedX_socks5` | TheSpeedX/PROXY-List | SOCKS5 | 2306 | 50 | 3 | **6.0%** | 0 | 4047.1ms | 634.3 |
| 23 | `TheSpeedX_socks4` | TheSpeedX/PROXY-List | SOCKS4 | 2468 | 50 | 2 | **4.0%** | 0 | 2077.4ms | 166.6 |
| 24 | `proxylist_to_http` | proxylist-to/proxy-list | HTTP | 750 | 50 | 2 | **4.0%** | 0 | 4003.8ms | 280.6 |
| 25 | `proxylist_to_socks5` | proxylist-to/proxy-list | SOCKS5 | 196 | 50 | 2 | **4.0%** | 0 | 2011.8ms | 415.4 |
| 26 | `jetkai_socks4` | jetkai/proxy-list | SOCKS4 | 1603 | 50 | 2 | **4.0%** | 0 | 2511.4ms | 442.3 |
| 27 | `jetkai_https` | jetkai/proxy-list | HTTPS | 2161 | 50 | 1 | **2.0%** | 0 | 4010.3ms | 1816.2 |
| 28 | `prxchk_http` | prxchk/proxy-list | HTTP | 58 | 50 | 1 | **2.0%** | 1 | 4179.0ms | 2356.6 |
| 29 | `jetkai_http` | jetkai/proxy-list | HTTP | 1801 | 50 | 0 | **0.0%** | 0 | 2007.0ms | — |
| 30 | `openproxylist_socks4` | roosterkid/openproxylist | SOCKS4 | 150 | 50 | 0 | **0.0%** | 0 | 2013.5ms | — |
| 31 | `openproxylist_socks5` | roosterkid/openproxylist | SOCKS5 | 10 | 10 | 0 | **0.0%** | 0 | 2002.5ms | — |
| 32 | `proxifly_https` | proxifly/free-proxy-list | HTTPS | 1103 | 50 | 0 | **0.0%** | 0 | 4003.2ms | — |
| 33 | `proxylist_to_socks4` | proxylist-to/proxy-list | SOCKS4 | 261 | 50 | 0 | **0.0%** | 0 | 2012.9ms | — |
| 34 | `prxchk_socks4` | prxchk/proxy-list | SOCKS4 | 32 | 32 | 0 | **0.0%** | 0 | 2006.3ms | — |
| 35 | `prxchk_socks5` | prxchk/proxy-list | SOCKS5 | 10 | 10 | 0 | **0.0%** | 0 | 2002.9ms | — |
| 36 | `vakhov_https` | vakhov/fresh-proxy-list | HTTPS | 6 | 6 | 0 | **0.0%** | 0 | 2000.7ms | — |

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