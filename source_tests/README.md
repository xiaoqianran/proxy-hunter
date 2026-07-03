# Source Tests — 分平台独立代理测试

每个代理来源**单独拉取、单独验证、单独出报告**，不聚合，用于对比各平台可用度。

## 结构

```
source_tests/
├── bootstrap_sources.py   # 生成 sources/*.json（39 个平台）
├── common.py              # 共用验证逻辑
├── run_one.py             # 测试单个平台
├── run_all.py             # 顺序测试全部平台
├── sources/               # 每个平台一个 JSON 配置
│   ├── monosans_http.json
│   ├── proxifly_http.json
│   └── ...
└── results/               # 每个平台独立输出
    ├── 00_RANKING.md      # 总排名（仅汇总，不混合代理池）
    ├── monosans_http.md
    ├── monosans_http.json
    └── ...
```

## 用法

```bash
cd source_tests

# 1. 生成 39 个平台配置
python bootstrap_sources.py

# 2. 测试单个平台
python run_one.py proxifly_http

# 3. 测试全部（约 30–60 分钟，39 平台 × 50 抽样）
python run_all.py
```

## 测试规则

- 验证端点：`icanhazip.com`（不用 httpbin）
- 每平台最多抽测 **50** 个（列表更大时随机抽样，保证公平对比）
- 25 并发，8 秒超时
- HTTP 通过后再测 HTTPS

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