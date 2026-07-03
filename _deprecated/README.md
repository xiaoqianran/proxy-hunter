# 作废归档 (_deprecated)

本目录存放**已排除、中断或结果被取代**的脚本与测试产出，仅供参考，不应再用于生产。

## 归档文件

| 文件 | 原用途 | 作废原因 |
|------|--------|----------|
| `test_proxies.py` | 第一轮多源代理质量测试 | 使用 `httpbin.org` 验证，该站点封禁代理流量，导致成功率虚低（~6.7%） |
| `proxy_hunter.py` | 22 源全量猎人 | 候选 11594 个，运行 12 分钟后手动终止；部分源有 bug（proxifly JSON、proxy-list.download 解包错误） |
| `run.sh` | 一键运行 `test_proxies.py` | 随 `test_proxies.py` 一并作废 |
| `results/report_20260703_104913.json` | 初轮测试原始数据 | 基于 httpbin，结论不可信 |
| `results/report_20260703_104913.md` | 初轮测试报告 | 同上 |
| `results/final_verified.json` | quick_hunt 结果的中间验证 | 已被 `ALL_WORKING.json` 取代 |
| `results/final_premium.txt` | 中间优质列表 | 已被 `ALL_PREMIUM.txt` 取代 |

## 有效替代方案

请使用项目根目录下的脚本：

```bash
.venv/bin/python quick_hunt.py      # 快速搜寻（~8 分钟）
.venv/bin/python geonode_hunt.py    # 深度搜寻（推荐）
.venv/bin/python final_verify.py    # 真实站点验证
.venv/bin/python generate_channel_reports.py  # 重新生成渠道 .md 报告
```

## 渠道报告

各渠道详细结果见 `../results/channels/` 目录。