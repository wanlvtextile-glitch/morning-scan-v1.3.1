# 早盘热点扫描

每日开盘前自动采集五路主源数据，识别热点板块与个股，由 LLM Agent 补全正宗度判断和综合结论，输出结构化早盘报告。

## 快速启动

```bash
pip install -r requirements.txt
cp .env.example .env
python cli.py check
python cli.py run
```

## 入口

| 入口 | 文件 | 说明 |
|------|------|------|
| CLI | `cli.py` | 终端、脚本、定时任务 |
| Skill | `run.py` | Claude Code 对话触发 |

常用命令：

```bash
python cli.py check
python cli.py run
python cli.py doctor
```

## 当前架构

```text
run.py / cli.py
  -> pipeline.py
  -> collector/
  -> analyzer.py
     -> preprocessor/
     -> sector_identifier/
     -> analysis/
     -> dual_score/
     -> editorial_layer/
     -> agents/
     -> output_layer/
```

当前主源：

- 淘股吧
- 同花顺早报
- 同花顺人气榜
- 雪球
- ZSXQ

## 环境要求

`.env` 至少需要：

- `XUEQIU_COOKIE`
- `AGENT_LAYER_ENABLED=true`
- `LLM_PROVIDER`
- `LLM_MODEL`
- 对应服务商的 API Key / Base URL

当前运行链路默认要求 Agent 层可用。环境校验不通过会直接中止，不再静默降级成纯 Python 报告。

## 输出文件

每次运行会归档到：

```text
runs/<timestamp>/
```

核心产物：

- `raw_news.json`
- `analysis_result.json`
- `YYYY-MM-DD-scan_result.json`
- `reports/YYYY-MM-DD-morning-scan.md`
- `reports/YYYY-MM-DD-morning-scan-brief.md`

根目录同名文件保留为最近一次运行的镜像。

## 报告口径

- `hotrank_signals` 是分析层全量人气信号。
- `hidden_signals` 只承接 `signal_type='hotrank_only'`。
- 最终报告保留 `人气榜隐藏信号` 段。
- 不再保留独立的 `人气先行信号` 分组。
- `stock_candidates` 必须来自有效的 `stock_branches`，不能回退为标题片段、机构名或句子噪声。

股票实体规则：

- 股票名称需要先通过实体有效性过滤，再做代码映射。
- 句子型短语、机构标签、研报抬头不会再进入最终股票表。
- 合法单股分支会被保留，不会因为聚合条数偏少被误杀。
- 无法稳定映射到股票字典的名称，不进入最终候选。

## 测试

```bash
python -m unittest discover -s tests
```

## 常见问题

**雪球数据失败**

检查 `XUEQIU_COOKIE` 是否过期。

**Agent 层未启用或调用失败**

检查 `AGENT_LAYER_ENABLED`、`LLM_PROVIDER`、`LLM_MODEL` 以及对应 API Key。当前不会静默降级。

**美股数据抓取失败（ProxyError）**

这是外部网络问题，通常不影响 A 股主报告生成。

## 最近更新

- `2026-05-13`：修复同花顺人气榜链路，统一以 `source_type='hotrank'` 识别。
- `2026-05-13`：收紧报告实体质量，修复伪股票名、跨板块数据复用和原文摘录噪声。
- `2026-05-13`：移除独立 `人气先行信号` 分组，仅保留 `人气榜隐藏信号` 展示。
