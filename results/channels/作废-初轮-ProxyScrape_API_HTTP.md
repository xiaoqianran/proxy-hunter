# ProxyScrape API (HTTP)

> **状态**: 作废轮次（使用 httpbin.org 验证，该站点封代理导致结果失真）
> **脚本**: `_deprecated/test_proxies.py`

## 来源信息

- **URL**: `https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all`
- **测试时间**: 2026-07-03T11:03:49.085096+00:00
- **验证 URL**: `http://httpbin.org/ip`

## 拉取结果

| 指标 | 值 |
|------|-----|
| 拉取成功 | 是 |
| 列表数量 | 669 |
| 抽样测试 | 30 |
| 可用数量 | 2 |
| 成功率 | 6.7% |
| HTTPS 可用 | 0 |

## 延迟统计

- 中位: 1400.1ms
- 平均: 1400.1ms
- 范围: 342.3-2457.9ms

## 可用代理

| 代理 | 延迟(ms) | HTTPS | 出口IP |
|------|----------|-------|--------|
| `http://178.212.144.7:80` | 342.3 | ✗ | 116.235.167.120 |
| `http://8.213.197.208:9080` | 2457.9 | ✗ | 8.213.197.208 |

## 常见错误

- `503, message='Attempt to decode JSON with unexpected mimetype: text/html', url='http://httpbin.org/ip'`
- `Cannot connect to host 129.226.149.231:3129 ssl:default [Connect call failed ('129.226.149.231', 3129)]`
- `Cannot connect to host 45.157.140.12:1081 ssl:default [Connect call failed ('45.157.140.12', 1081)]`
- `502, message='Attempt to decode JSON with unexpected mimetype: ', url='http://httpbin.org/ip'`
- `Cannot connect to host 178.156.224.42:3129 ssl:default [Connect call failed ('178.156.224.42', 3129)]`