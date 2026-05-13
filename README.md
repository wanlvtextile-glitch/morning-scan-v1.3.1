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

## 目录结构

```text
.
├── cli.py                          # 终端入口（check / run / doctor）
├── run.py                          # Claude Code Skill 入口
├── pipeline.py                     # 全流程协调 + 唯一文件 I/O 层
├── analyzer.py                     # 分析层入口（纯计算，不写文件）
├── checks.py                       # 启动前环境校验
│
├── collector/                      # 数据采集层
│   ├── entry.py                    # collect() 对外入口
│   ├── orchestrator.py             # 并发调度 + CollectorOutput 组装
│   ├── sources.py                  # 淘股吧 / 同花顺 / 雪球 抓取
│   ├── zsxq_source.py              # 知识星球 REST API 采集
│   ├── social_sources.py           # 社交源公共工具函数
│   ├── registry.py                 # 数据源注册表
│   ├── models.py                   # NewsItem / SourceResult / CollectorOutput
│   ├── http_client.py              # 全局 HTTP 预算 + fetch_with_retry
│   ├── market_data.py              # 美股行情采集
│   └── time_window.py              # 时间窗口计算（A股交易日逻辑）
│
├── preprocessor/                   # 预处理层（去重 / 聚类 / 信号标注）
│   ├── entry.py
│   ├── rules.py
│   ├── cluster.py
│   ├── evidence.py
│   ├── conclusions.py
│   ├── downstream.py
│   ├── output.py
│   └── report.py
│
├── sector_identifier/              # 板块识别层
│   ├── entry.py
│   ├── rules.py
│   ├── evidence.py
│   ├── conclusions.py
│   ├── downstream.py
│   ├── output.py
│   └── report.py
│
├── analysis/                       # 分析层（星级评分 / 阶段判断）
│   ├── entry.py
│   ├── scorer.py
│   ├── stage_rules.py
│   ├── stage_definitions.py
│   ├── conclusions.py
│   ├── downstream.py
│   ├── output.py
│   └── report.py
│
├── dual_score/                     # 双维评分层（持续性 / 发酵概率）
│   ├── entry.py
│   ├── continuation.py
│   ├── fermentation.py
│   ├── downstream.py
│   ├── output.py
│   └── report.py
│
├── editorial_layer/                # 编辑层（报告分组 / 个股合并 / 逻辑摘要）
│   ├── entry.py
│   ├── sector_builder.py
│   ├── stock_merger.py
│   ├── logic_summary.py
│   ├── recommendations.py
│   ├── report_package.py
│   ├── market_context.py
│   └── downstream.py
│
├── agents/                         # LLM Agent 层
│   ├── entry.py
│   ├── state.py
│   ├── interface.py
│   ├── config.py
│   ├── base.py
│   ├── impl/
│   │   ├── info_enrichment.py      # 信息补全 Agent
│   │   └── semantic_judgment.py    # 语义判断 Agent
│   ├── prompts/                    # 各 Agent 提示词
│   └── provider/                   # LLM 供应商适配（Anthropic / OpenAI-compat）
│
├── output_layer/                   # 输出层（Markdown 报告渲染）
│   ├── entry.py                    # build_report_from_editorial() 唯一出口
│   ├── report.py
│   ├── logic_render.py
│   ├── rules.py
│   ├── conclusions.py
│   ├── downstream.py
│   └── output.py
│
├── config/                         # 运行时配置（无凭据）
│   ├── agent_config.json           # Agent 开关 / 限流
│   ├── source_registry.json        # 数据源注册
│   ├── social_sources.json         # 社交源配置
│   └── zsxq_source.json            # 知识星球采集参数
│
├── data/
│   └── stocks_dict.csv             # A 股股票字典（实体校验用）
│
├── skill/                          # Skill 运维文档
│   ├── SKILL.md                    # 项目维护主文档
│   ├── MORNING_SCAN_RUNTIME_RULES.md
│   └── ZSXQ_LIVE_COLLECTION.md
│
├── tests/                          # 回归测试套件（51 个测试）
│
├── reports/                        # 报告归档目录（运行时生成，不入库）
├── runs/                           # 每次运行完整归档（不入库）
│
├── .env.example                    # 环境变量模板
├── requirements.txt
└── GUIDE.md                        # 运维操作指南
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
