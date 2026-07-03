# Source Tests — 分平台独立代理测试

每个代理来源**单独拉取、单独验证、单独出报告**，不聚合，用于对比各平台可用度。

---

## 推荐：standard 模式（~18 秒 / 39 平台）

直接运行 `run_all.py` 即为推荐配置，无需额外参数：

```bash
cd source_tests
python run_all.py
```

| 项 | 值 |
|----|-----|
| 平台并行 | 8 workers |
| 验证并发 | 80 |
| 超时 | 4 秒 |
| 抽样 | 50 个/平台 |
| 典型耗时 | **~18 秒**（冷/热启动差距 < 1 秒） |

---

## 结构

```
source_tests/
├── bootstrap_sources.py   # 生成 sources/*.json（39 个平台）
├── common.py              # 共用拉取 + 验证逻辑
├── run_one.py             # 测试单个平台
├── run_all.py             # 并行测试全部平台
├── .cache/                # 列表缓存（1h TTL，git 忽略）
├── sources/               # 每个平台一个 JSON 配置
└── results/               # 每个平台独立输出
    ├── 00_RANKING.md      # 总排名
    ├── {source_id}.md
    └── {source_id}.json
```

---

## 用法

```bash
# 1. 生成 39 个平台配置（首次或更新来源时）
python bootstrap_sources.py

# 2. 测试单个平台（~3–5 秒）
python run_one.py proxifly_http

# 3. 测试全部 — 推荐，~18 秒
python run_all.py

# 4. 断点续跑：跳过 1 小时内已有结果
python run_all.py --skip-existing

# 5. 只测指定平台
python run_all.py --only vakhov_http,proxyscrape_api_http

# 6. 强制重新拉列表（忽略 .cache/）
python run_all.py --no-cache
```

### 可选：turbo 模式

```bash
python run_all.py --turbo   # ~11 秒，超时 3.5s，SOCKS 漏检更多，仅适合粗筛
```

---

## CLI 参数

| 参数 | 默认（standard） | 说明 |
|------|-----------------|------|
| `--workers` | 8 | 同时跑几个平台 |
| `--concurrency` | 80 | 每平台验证并发数 |
| `--timeout` | 4 | 单次请求超时（秒） |
| `--max-test` | 50 | 每平台抽样上限 |
| `--skip-existing` | off | 跳过 1h 内新鲜结果 |
| `--no-cache` | off | 忽略 `.cache/`，强制重新拉列表 |
| `--no-prefetch` | off | 跳过并行预取列表 |
| `--no-https` | off | 跳过 HTTPS 检测 |
| `--turbo` | off | workers=12 / concurrency=120 / timeout=3.5 |
| `--only` | — | 逗号分隔的 source id |

`run_one.py` 支持 `--concurrency`、`--timeout`、`--max-test`、`--no-cache`、`--no-https`。

---

## 性能演进

| 版本 | 39 平台耗时 | 关键手段 |
|------|------------|----------|
| v1 顺序 | ~635s | 逐平台、逐代理建 Session |
| v2 并行 | ~68s | 共享 Session、4 workers、列表缓存 |
| **v3 standard（默认）** | **~18s** | uvloop、单遍 HTTP+HTTPS、8 workers、预取 |
| v3 turbo | ~11s | 更高并发 + 更短超时，准确率下降 |

### v3 架构要点

1. **单遍探测** — HTTP 命中后同一 Session 立刻测 HTTPS
2. **uvloop** — Linux 下替换默认事件循环
3. **并行预取** — 验证前 12 路并发拉完全部列表
4. **解析缓存** — `.cache/{id}.proxies.json` 跳过重复 parse
5. **响应截断** — 只读 96 字节拿出口 IP
6. **异步写盘** — `asyncio.to_thread` 写报告不阻塞验证

---

## 常见问题

### 列表缓存会让结果「假快」吗？

不会显著影响。`.cache/` 只缓存拉下来的代理列表（预取省 ~0.3s）。**99%+ 耗时在验证代理是否可用**，冷启动 `--no-cache` 与有缓存均在 17–18 秒。

### 跑得快会漏检代理吗？

standard 模式（4s 超时）与保守模式（6s 超时）在**同一批固定样本**上命中率基本一致。每次跑成功率波动主要来自：

- 免费代理本身不稳定（同一代理几秒前后结果可能不同）
- 每平台随机抽 50 个，每次样本不同

`--turbo` 因超时更短，慢代理更容易被判死，不适合作为默认。

### `--skip-existing` 是什么？

跳过 1 小时内有 `results/{id}.json` 的平台，适合定时增量刷新，可大幅缩短二次运行时间。

---

## 测试规则

- 验证端点：`icanhazip.com`（不用 httpbin）
- 每平台最多抽测 **50** 个（列表更大时随机抽样）
- HTTP 通过后再测 HTTPS（可用 `--no-https` 关闭）

---

## 平台列表（39 个）

| 分组 | Source IDs |
|------|------------|
| monosans | `monosans_http`, `monosans_http_anonymous` |
| jetkai | `jetkai_http`, `jetkai_https`, `jetkai_socks4`, `jetkai_socks5` |
| Proxifly CDN | `proxifly_all`, `proxifly_http`, `proxifly_https`, `proxifly_socks4`, `proxifly_socks5` |
| ProxyScrape | `proxyscrape_api_http/socks4/socks5`, `proxyscrape_mirror_http` |
| vakhov | `vakhov_http/https/socks4/socks5` |
| TheSpeedX | `TheSpeedX_http/socks4/socks5` |
| roosterkid | `openproxylist_https/socks4/socks5` |
| databay | `databay_http`, `databay_socks5` |
| iplocate | `iplocate_http`, `iplocate_socks5` |
| 补充 | `prxchk_*`, `proxylist_to_*`, `hookzof_socks5`, `mmpx12_http`, `ErcinDedeoglu_http`, `ShiftyTR_http` |