# 免费高质量代理搜寻 — 最终报告

**测试时间**: 2026-07-03  
**测试方法**: 22+ 来源拉取 → 两轮验证 → 真实站点实测（icanhazip / Google / Moltbook API）  
**关键发现**: 上次测试失败是因为 `httpbin.org` 会封代理流量；改用 `icanhazip.com` 后成功率从 **6.7%** 跃升至 **4%+**（优质层）

---

## 最终成果

| 指标 | 数量 |
|------|------|
| 扫描代理候选 | **11,594**（全量源）+ **1,931**（Geonode 精准） |
| 两轮验证通过 | **77** 个可用 |
| 优质（HTTPS + 延迟<3s） | **11** 个 |
| 实测可爬 Moltbook | **8** 个 ⭐ |

---

## ⭐ TOP 8 — 可直接用于爬虫（全部通过 Moltbook API 实测）

| # | 代理 | 延迟 | 协议 | 出口 IP | HTTPS | Google | Moltbook |
|---|------|------|------|---------|-------|--------|----------|
| 1 | `http://43.133.15.47:3128` | **229ms** | HTTP | 43.133.15.47 | ✓ | ✓ | ✓ |
| 2 | `socks5://193.25.215.182:22222` | **232ms** | SOCKS5 | 193.25.215.182 | ✓ | ✓ | ✓ |
| 3 | `http://62.90.70.144:7443` | **395ms** | HTTP | 62.90.70.144 | ✓ | ✓ | ✓ |
| 4 | `http://185.181.209.34:8080` | **588ms** | HTTP | 185.181.209.34 | ✓ | ✓ | ✓ |
| 5 | `socks5://5.255.113.177:1080` | **605ms** | SOCKS5 | 5.255.113.177 | ✓ | ✓ | ✓ |
| 6 | `socks5://212.77.75.25:1088` | **803ms** | SOCKS5 | 212.77.75.20 | ✓ | ✓ | ✓ |
| 7 | `socks5://127.0.0.1:9050` | **1181ms** | Tor | 45.9.156.22 | ✓ | ✓ | ✓ |
| 8 | `http://112.28.149.152:8443` | **1218ms** | HTTP | 212.87.194.7 | ✓ | ✓ | ✓ |

> 推荐首选 `#1` 和 `#2`，速度最快且全项通过。

---

## 全部 77 个可用代理

见 `ALL_WORKING.json`，按延迟排序。

### 优质层（11 个，支持 HTTPS）

见 `ALL_PREMIUM.txt`

### 普通 HTTP 层（66 个）

支持 HTTP 请求，多数不支持 HTTPS 隧道，适合爬 HTTP 接口。

---

## 最佳来源排名（按产出质量）

| 来源 | 策略 | 产出 |
|------|------|------|
| **Geonode API**（elite + google + uptime≥80%） | 按速度/延迟排序，过滤 | 最多优质代理 |
| **monosans/proxy-list** | 精选小列表，质量高 | HTTPS 代理主力 |
| **jetkai/proxy-list** | 大量在线代理 | 量大但需筛选 |
| **Tor（本地）** | `apt install tor` | 100% 可用，较慢 |
| ProxyScrape API | 量大 | 需大量筛选 |
| OpenProxyList | 量最大（5686+） | 存活率极低 |

---

## 使用方法

### Python aiohttp

```python
import aiohttp

PROXY = "http://43.133.15.47:3128"

async with aiohttp.ClientSession() as session:
    async with session.get("https://www.moltbook.com/api/v1/homepage", proxy=PROXY) as resp:
        data = await resp.json()
```

### SOCKS5 代理

```python
from aiohttp_socks import ProxyConnector

connector = ProxyConnector.from_url("socks5://193.25.215.182:22222")
async with aiohttp.ClientSession(connector=connector) as session:
    async with session.get("https://www.moltbook.com/api/v1/homepage") as resp:
        ...
```

### 代理池轮换

```python
proxies = open("results/BEST_FOR_CRAWLING.txt").read().splitlines()
proxy = proxies[request_count % len(proxies)]
```

### Tor

```bash
sudo apt install tor && sudo systemctl start tor
# SOCKS5: 127.0.0.1:9050
curl --socks5-hostname 127.0.0.1:9050 https://icanhazip.com
```

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `BEST_FOR_CRAWLING.txt` | ⭐ 8 个实测可爬 Moltbook 的代理 |
| `ALL_PREMIUM.txt` | 11 个 HTTPS 优质代理 |
| `ALL_WORKING.json` | 全部 77 个可用代理 + 元数据 |
| `PREMIUM_VERIFIED.json` | 优质代理真实站点验证详情 |
| `channels/` | **各渠道分报告 (.md)**，见 `channels/00-总览.md` |
| `FINAL_REPORT.md` | 本报告 |

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `geonode_hunt.py` | 推荐：Geonode 深度搜寻 + 合并 |
| `quick_hunt.py` | 快速精选源猎人 |
| `final_verify.py` | 真实站点验证 |
| `generate_channel_reports.py` | 从 JSON 重新生成各渠道 .md |
| `_deprecated/` | 作废脚本（test_proxies、proxy_hunter 等） |

---

## 重要提醒

1. **免费代理衰减极快**，建议每次爬取前运行 `geonode_hunt.py` 刷新
2. **不要用 httpbin.org 测代理**，会被封；用 `icanhazip.com`
3. **透明代理会泄露真实 IP**（如 `183.89.247.182`），已在筛选中排除
4. **Tor 最稳定**但慢（~1s），适合低频匿名请求
5. 爬 Moltbook 建议配合限速（1-2 req/s），即使用代理也不要过猛