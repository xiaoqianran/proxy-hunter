# Proxy Hunter

**从 20+ 来源搜寻、验证、排名免费代理的 Python 异步工具包。**

[English](README.md)

---

## 为什么做这个项目？

大多数免费代理教程用 **httpbin.org** 做验证，但该站点会封代理流量，导致所有来源看起来都不可用（成功率约 5%）。本项目改用 **icanhazip.com** 及真实目标站点验证。

实测数据（2026-07-03）：

| 指标 | 结果 |
|------|------|
| 扫描候选 | 11,000+ |
| 可用代理 | **77** |
| 优质（HTTPS + <3s） | **11** |
| 可爬 Moltbook API | **8** |

---

## 快速开始

```bash
git clone https://github.com/xiaoqianran/proxy-hunter.git
cd proxy-hunter

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 推荐：深度搜寻（约 8–10 分钟）
python geonode_hunt.py

# 查看可用代理
cat results/BEST_FOR_CRAWLING.txt
```

> 搜寻脚本大部分时间花在**验证约 1900 个代理**上（25 并发、8 秒超时），拉列表只需约 30 秒。

---

## 脚本说明

| 脚本 | 用途 | 典型耗时 |
|------|------|----------|
| `geonode_hunt.py` | 深度搜寻（推荐） | **8–10 分钟** |
| `quick_hunt.py` | 快速搜寻（两轮验证） | **8–9 分钟** |
| `final_verify.py` | 真实站点验证 | ~1 分钟 |
| `generate_channel_reports.py` | 生成各渠道 .md 报告 | <1 秒 |

### `geonode_hunt.py` 耗时说明

实测（2026-07-03）：

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 拉取列表 | ~30 秒 | Geonode API + GitHub 列表 |
| 验证代理 | ~8 分钟 | 1908 个候选，25 并发 |
| **合计** | **~8.5 分钟** | 找到 77 可用，11 优质 |

| 场景 | 预计时间 |
|------|----------|
| 首次运行 | 8–10 分钟 |
| 再次运行（跳过已知代理） | 5–8 分钟 |
| 网络较慢 | 最长约 15 分钟 |

想加速可改 `geonode_hunt.py` 里的 `TIMEOUT` 或减少 Geonode 翻页数，但找到的代理会变少。

作废脚本见 `_deprecated/README.md`。

---

## 注意事项

1. 不要用 httpbin.org 测代理
2. 免费代理几小时就会失效，爬取前先刷新
3. 即使用代理也要限速（建议 1–2 req/s）

---

## 许可证

MIT