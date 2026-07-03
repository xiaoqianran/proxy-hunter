# Geonode API

> **状态**: 作废轮次（使用 httpbin.org 验证，该站点封代理导致结果失真）
> **脚本**: `_deprecated/test_proxies.py`

## 来源信息

- **URL**: `https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols=http,socks5`
- **测试时间**: 2026-07-03T11:03:49.085096+00:00
- **验证 URL**: `http://httpbin.org/ip`

## 拉取结果

| 指标 | 值 |
|------|-----|
| 拉取成功 | 是 |
| 列表数量 | 100 |
| 抽样测试 | 30 |
| 可用数量 | 0 |
| 成功率 | 0.0% |
| HTTPS 可用 | 0 |

## 可用代理

无

## 常见错误

- `503, message='Attempt to decode JSON with unexpected mimetype: text/html', url='http://httpbin.org/ip'`
- `[Errno 111] Couldn't connect to proxy 206.123.156.242:6980 [Connect call failed ('206.123.156.242', 6980)]`
- `[Errno 111] Couldn't connect to proxy 206.123.156.229:6988 [Connect call failed ('206.123.156.229', 6988)]`
- `[Errno 111] Couldn't connect to proxy 206.123.156.215:9904 [Connect call failed ('206.123.156.215', 9904)]`
- `Cannot connect to host 223.206.56.218:8080 ssl:default [Connect call failed ('223.206.56.218', 8080)]`