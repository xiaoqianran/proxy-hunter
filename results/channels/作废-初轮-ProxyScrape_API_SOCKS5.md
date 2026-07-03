# ProxyScrape API (SOCKS5)

> **状态**: 作废轮次（使用 httpbin.org 验证，该站点封代理导致结果失真）
> **脚本**: `_deprecated/test_proxies.py`

## 来源信息

- **URL**: `https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all`
- **测试时间**: 2026-07-03T11:03:49.085096+00:00
- **验证 URL**: `http://httpbin.org/ip`

## 拉取结果

| 指标 | 值 |
|------|-----|
| 拉取成功 | 是 |
| 列表数量 | 578 |
| 抽样测试 | 30 |
| 可用数量 | 0 |
| 成功率 | 0.0% |
| HTTPS 可用 | 0 |

## 可用代理

无

## 常见错误

- `503, message='Attempt to decode JSON with unexpected mimetype: text/html', url='http://httpbin.org/ip'`
- `[Errno 111] Couldn't connect to proxy 166.62.88.163:45842 [Connect call failed ('166.62.88.163', 45842)]`
- `[Errno 111] Couldn't connect to proxy 103.61.122.229:1081 [Connect call failed ('103.61.122.229', 1081)]`
- `[Errno 111] Couldn't connect to proxy 221.176.85.229:1081 [Connect call failed ('221.176.85.229', 1081)]`