# Source Tests — 分平台独立代理测试

每个代理来源**单独拉取、单独验证、单独出报告**，不聚合，用于对比各平台可用度。

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

## 用法

```bash
cd source_tests

# 1. 生成 39 个平台配置
python bootstrap_sources.py

# 2. 测试单个平台
python run_one.py proxifly_http

# 3. 测试全部（v3 约 30–50 秒 / 39 平台）
python run_all.py

# 4. 极限模式（uvloop + 更高并发）
python run_all.py --turbo

# 5. 断点续跑：跳过 1 小时内已有结果
python run_all.py --skip-existing

# 6. 只测指定平台
python run_all.py --only vakhov_http,proxyscrape_api_http
```

## CLI 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--workers` | 8 | 同时跑几个平台 |
| `--concurrency` | 80 | 每平台验证并发数 |
| `--timeout` | 4 | 单次请求超时（秒） |
| `--max-test` | 50 | 每平台抽样上限 |
| `--turbo` | off | 极限：workers=12 concurrency=120 timeout=3.5 |
| `--skip-existing` | off | 跳过 1h 内新鲜结果 |
| `--no-cache` | off | 忽略 `.cache/`，强制重新拉列表 |
| `--no-prefetch` | off | 跳过并行预取列表 |
| `--no-https` | off | 跳过 HTTPS 检测（更快） |
| `--only` | — | 逗号分隔的 source id |

`run_one.py` 支持 `--concurrency`、`--timeout`、`--max-test`、`--no-cache`、`--no-https`、`--turbo`。

## 性能优化

| 版本 | 39 平台耗时 | 关键手段 |
|------|------------|----------|
| v1 顺序 | ~635s | 逐平台、逐代理建 Session |
| v2 并行 | ~68s | 共享 Session、4 workers、列表缓存 |
| v3 极限 | ~30–40s | uvloop、单遍 HTTP+HTTPS、8 workers、预取、解析缓存 |

v3 细节：

1. **单遍探测** — HTTP 命中后同一 Session 立刻测 HTTPS，消灭二阶段等待
2. **uvloop** — Linux 下替换默认事件循环
3. **并行预取** — 验证前 12–16 路并发拉完全部列表
4. **解析缓存** — `.cache/{id}.proxies.json` 跳过重复 parse
5. **响应截断** — 只读 96 字节拿出口 IP
6. **异步写盘** — `asyncio.to_thread` 写报告不阻塞验证

## 测试规则

- 验证端点：`icanhazip.com`（不用 httpbin）
- 每平台最多抽测 **50** 个（列表更大时随机抽样）
- HTTP 通过后再测 HTTPS（可用 `--no-https` 关闭）

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