# Proxy Hunter

**分平台独立测试免费代理** — 从 39 个公开来源分别拉取、验证、排名，不混合代理池。

[English](README.md) · 详细文档见 [`source_tests/README.md`](source_tests/README.md)

---

## 为什么需要这个项目？

多数教程用 **httpbin.org** 验证代理，但该站会拦截代理流量，导致所有来源看起来都不可用。本项目用 **icanhazip.com** 对每个平台**单独测试**，排名才有参考价值。

---

## 快速开始

```bash
git clone https://github.com/xiaoqianran/proxy-hunter.git
cd proxy-hunter

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd source_tests
python bootstrap_sources.py          # 生成 39 个平台配置
python run_one.py proxifly_http    # 测单个平台（~3–5 秒）
python run_all.py                  # 测全部 39 个（推荐，~18 秒）
```

---

## 推荐模式：standard（~18 秒）

默认 `run_all.py` 即 **standard 模式**，在速度和准确率之间取得平衡，适合日常使用：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 平台并行 | 8 workers | 同时测 8 个来源 |
| 验证并发 | 80 | 每平台最多 80 路并发探测 |
| 超时 | 4 秒 | 死代理快速淘汰 |
| 抽样 | 50 个/平台 | 列表更大时随机抽样 |

**39 平台全量跑测约 18 秒**（冷启动无列表缓存亦在 17–18 秒左右）。耗时主要在代理验证（占 99%+），列表缓存仅节省不到 1 秒预取时间。

```bash
# 日常推荐
python run_all.py

# 断点续跑：跳过 1 小时内已有结果的平台
python run_all.py --skip-existing

# 只测指定平台
python run_all.py --only vakhov_http,proxyscrape_api_http
```

> `--turbo`（~11 秒）更快但超时更短，SOCKS 类平台漏检更多，仅适合快速粗筛。

---

## 目录结构

```
proxy-hunter/
└── source_tests/
    ├── bootstrap_sources.py   # 生成 sources/*.json
    ├── common.py              # 拉取 + 验证核心逻辑
    ├── run_one.py             # 单平台测试
    ├── run_all.py             # 全平台并行测试
    ├── .cache/                # 列表缓存（1h TTL，git 忽略）
    ├── sources/               # 每平台一个 JSON 配置（39 个）
    └── results/               # 每平台独立 .md / .json 报告
        └── 00_RANKING.md      # 总排名
```

---

## 实测 TOP 5（2026-07-03，standard 模式）

完整排名：[`source_tests/results/00_RANKING.md`](source_tests/results/00_RANKING.md)

| 排名 | 平台 | 协议 | 成功率 |
|------|------|------|--------|
| 1 | vakhov/fresh-proxy-list | HTTP | **70%** |
| 2 | monosans/proxy-list | HTTP | **46%** |
| 3 | ProxyScrape API v4 | HTTP Elite | **46%** |
| 4 | Proxifly CDN | HTTP | **44%** |
| 5 | ErcinDedeoglu/proxies | HTTP | **28%** |

> 免费代理不稳定，每次跑成功率会有波动，属正常现象；standard 模式与保守参数（6s 超时）在同一批样本上命中率基本一致。

---

## 性能演进

| 版本 | 39 平台耗时 | 说明 |
|------|------------|------|
| v1 顺序执行 | ~635s | 逐平台、逐代理建连 |
| v2 并行 | ~68s | 共享 Session、4 workers |
| **v3 standard（当前默认）** | **~18s** | uvloop、单遍 HTTP+HTTPS、8 workers、并行预取 |

v3 关键优化：HTTP 命中后同一 Session 立刻测 HTTPS；Linux 下启用 uvloop；验证前并行预取全部列表；报告异步写盘不阻塞探测。

---

## 测试规则

- 验证端点：`icanhazip.com`（不用 httpbin）
- 每平台最多抽测 **50** 个代理
- HTTP 通过后再测 HTTPS（`--no-https` 可跳过）
- 每个平台独立出报告，**不聚合代理池**

---

## 作为 Python 依赖（供爬虫等项目）

v0.3+ 提供可安装包 `proxy_hunter`：

```bash
pip install -e /path/to/proxy-hunter
# 或 uv: proxy-hunter = { path = "../proxy-hunter", editable = true }
```

```python
from proxy_hunter import load_pool_from_results

pool = load_pool_from_results()  # 默认读 source_tests/results/
proxy_url = pool.acquire()         # 轮询取代理
# ... aiohttp.get(url, proxy=proxy_url) ...
pool.report(proxy_url, success=True)
```

详见 [moltbook-crawler](../moltbook-crawler) 的 `--proxy` 集成示例。

---

## 在代码中使用

从 `source_tests/results/{platform}.json` 读取可用代理：

```python
import aiohttp

PROXY = "http://43.133.15.47:3128"  # 来自 results/vakhov_http.json

async with aiohttp.ClientSession() as session:
    async with session.get("https://example.com", proxy=PROXY) as resp:
        print(await resp.text())
```

---

## 许可证

MIT — 见 [LICENSE](LICENSE)