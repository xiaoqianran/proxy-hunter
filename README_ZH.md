# Proxy Hunter

**分平台独立测试免费代理** — 从 39 个公开来源分别拉取、验证、排名，不混合代理池。

[English](README.md)

---

## 快速开始

```bash
git clone https://github.com/xiaoqianran/proxy-hunter.git
cd proxy-hunter

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd source_tests
python bootstrap_sources.py
python run_one.py proxifly_http   # 测单个平台
python run_all.py                 # 测全部 39 个（约 10 分钟）
```

---

## 目录结构

```
proxy-hunter/
└── source_tests/
    ├── sources/     # 每平台一个 JSON 配置
    └── results/     # 每平台独立 .md / .json 报告
        └── 00_RANKING.md
```

---

## 实测 TOP 5（2026-07-03）

| 平台 | 协议 | 成功率 |
|------|------|--------|
| vakhov | SOCKS4 | 86% |
| ProxyScrape API v4 | HTTP | 68% |
| ProxyScrape API v4 | SOCKS5 | 58% |
| vakhov | HTTP | 56% |
| Proxifly CDN | HTTP | 42% |

---

## 许可证

MIT