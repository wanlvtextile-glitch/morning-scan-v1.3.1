---
name: market-morning-scan
description: 开盘前采集市场热点，筛选当天可能发酵的板块和个股，由 LLM Agent 补全正宗度判断和结论，输出早盘报告
---

# 早盘热点扫描 v1.3

## 触发条件

用户说「启动早盘扫描」、「早盘热点」、「扫描市场」或类似表达时激活。

---

## 项目结构

```
项目根目录/
├── run.py                    ← 唯一入口，识别触发词后启动 pipeline
├── pipeline.py               ← 全流程串联（采集 → 分析 → agent → 报告）
├── analyzer.py               ← 分析编排入口
├── stocks_dict.csv           ← 全量 A 股名称词典（5246条，个股提取必需）
├── requirements.txt          ← 生产依赖
├── .env                      ← 运行配置（从 .env.example 复制后填写）
├── .env.example              ← 配置模板
├── config/
│   └── agent_config.json     ← Agent 节点开关与费用控制
├── collector/                ← 采集层（四源并行 + akshare 市场数据）
├── preprocessor/             ← 预处理层（去重 / recap / catalyst）
├── sector_identifier/        ← 题材识别层（9板块 + cross-sector 权重）
├── analysis/                 ← 分析层（评分 / 阶段 / 个股提取）
├── dual_score/               ← 双评分层（续强 / 发酵 / 验证点）
├── editorial_layer/          ← 编辑层（整合 editorial_result 结构）
├── agents/                   ← Agent 层（LLM 补全正宗度/结论，v1.3）
│   ├── impl/                 ← InfoEnrichmentAgent / SemanticJudgmentAgent
│   ├── prompts/              ← 6个提示词 txt（可热更新，不改代码）
│   └── provider/             ← Anthropic / OpenAI-compatible / factory
├── output_layer/             ← 输出层（生成 Markdown 报告）
└── reports/                  ← 报告输出目录（.gitkeep 保持目录存在）
```

**运行时产物**（每次运行后生成，不进版本控制）：
- `raw_news.json`：采集层原始输出
- `analysis_result.json`：分析层中间产物
- `YYYY-MM-DD-scan_result.json`：含 agent 补全的最终结构化产物
- `reports/YYYY-MM-DD-morning-scan.md`：主报告
- `reports/YYYY-MM-DD-morning-scan-brief.md`：简报

---

## 执行步骤

### Step 1：运行数据采集与分析

```bash
python cli.py run
```

此命令自动完成全流程：采集 → 预处理 → 题材识别 → 分析 → 双评分 → 编辑层 → **Agent 层补全** → 报告草稿生成。

> 若 `.env` 配置不完整（缺少 `XUEQIU_COOKIE` 或 LLM Key），命令立即报错退出，提示缺失字段及填写位置。按提示填写 `.env` 后重新执行即可。

记录输出中的：
- 各源 `fetch_success` 状态（淘股吧 / 同花顺早报 / 同花顺人气榜 / 雪球）
- `confidence` 值（normal / low / none）
- Agent 层调用次数和耗时

> ⚠️ 禁止将采集和分析拆分为两条独立命令执行。

---

### Step 2：读取结构化分析结果

优先读取 `YYYY-MM-DD-scan_result.json`（含 agent 补全字段）；agent 层未启用时回退读 `analysis_result.json`。

重点关注字段：

**板块层（`sectors[]`）：**
- `name` / `star_rating`（1-5星）/ `stage`（预发酵/发酵中/已高潮/unknown）
- `effective_count`：跨板块权重后的有效条目数
- `stock_candidates[]`：个股候选，含 agent 预填的 `authenticity` / `evidence` / `reason`
- `agent_review`：`{note, confidence}` Agent 审核备注
- `top_items[]`：最多8条代表性新闻，含 `cross_sector_weight`
- `needs_websearch`：true = 人气榜 hotrank_only 信号，需 WebSearch 补充

**人气信号（`hotrank_signals[]`）：**
- `signal_type = "hotrank_only"` [!!]：新闻极少 → 必须 WebSearch 补充
- `signal_type = "hotrank_weak"` [~]：需人工评估
- `signal_type = "news_driven"` [OK]：信号强

**隐藏信号（`editorial.hidden_signals[]`）：**
- `websearch_summary`：Agent 已生成的 hotrank 背景摘要
- `focus_stocks`：Agent 推断的关注个股

**综合结论：**
- `editorial.final_recommendations.conclusion_text`：Agent 生成的结论段落

---

### Step 3：WebSearch 补充

> 从 `analysis_result.json` 读取日期字段：
> - `{a_stock_date}`：`time_window_start` 前10位，格式化为「YYYY年M月D日」
> - `{us_market_date}`：`us_market_date` 字段，同格式

**查询 1（A股指数）：** `上证指数 深证成指 创业板指 {a_stock_date} 收盘价`

**查询 2（隔夜美股）：** `{us_market_date} 美股 收盘 走强 走弱 板块 中概股`

**查询 3（hotrank_only 专项）：** 对每个 `!!` 信号板块执行一次，补充 `focus_stocks`（若 agent 未填充）：
- 格式：`{板块名} A股 今日`
- 结果标注为「人气榜补充源」，热度不超过 ⭐⭐⭐

---

### Step 4：正宗度审核

**Agent 已预填** `stock_candidates[].authenticity / evidence / reason`，Claude 负责审核与覆盖。

若 agent 判断有误，在报告中注明覆盖原因并修正。标准：

| 判断 | 标准 |
|------|------|
| 核心股 | 主营直接覆盖题材，行业/细分龙头 |
| 边缘受益 | 有关联但非主业 |
| 蹭概念 | 仅关键词相关，无基本面支撑 |

> 必须先检查 `top_items` 文本，确认 agent 未遗漏高频提及股票。若有遗漏，手动补充，代码填「待查」。

---

### Step 5：审核 Python 结论（可选覆盖）

Python 已完成双评分和分组，此步骤仅在发现明显偏差时覆盖，并在报告中注明覆盖原因：

- `group` 分组与 `top_items` 内容明显矛盾
- `stage = unknown` 且 top_items 有明确信号 → 人工判定最接近的阶段
- `continuation_score` / `fermentation_score` 与 WebSearch 实时信息冲突

---

### Step 6：输出最终报告

从 Python 草稿 `reports/YYYY-MM-DD-morning-scan.md` 开始，补全以下内容：

1. **数据采集状态表**（Step 1 各源状态）
2. **市场背景数据**（Step 3 查询 1+2 结果）
3. **个股正宗度表**（Step 4 结果，或审核 agent 预填内容）
4. **人气先行信号摘要**（Step 3 查询 3，或 agent `websearch_summary`）

**输出前检查清单：**

- [ ] 4个分组均有输出，无候选时写「暂无」
- [ ] 每板块有 stage 标签 + ⭐ 评分
- [ ] 主线/发酵候选：每板块含 continuation/fermentation 评分
- [ ] 每板块个股正宗度已填写，依据非空
- [ ] 次日发酵候选：展示 trigger_points
- [ ] 状态栏使用 ✅/⚠️/❌
- [ ] 人气先行信号含 hotrank_only 板块摘要

> ⚠️ 上述任意一项未满足，禁止输出报告正文。

使用 Write 工具覆盖写入 `reports/YYYY-MM-DD-morning-scan.md`。

---

## 报告格式模板

```
# 早盘热点扫描 · {YYYY-MM-DD}
生成时间：{HH:MM}

## 数据采集状态
| 来源 | 状态 | 条目数 |
|------|------|--------|
| 淘股吧 | ✅/⚠️/❌ | n 条 |
| 同花顺早报 | ✅/⚠️/❌ | n 条 |
| 同花顺人气榜 | ✅/⚠️/❌ | n 条 |
| 雪球 | ✅/⚠️/❌ | n 条 |

主源成功：n/4　置信度：正常/低/无数据
去重：原始 N 条 → 去重后 M 条

## 市场背景
| 指数 | 昨收 | 涨跌 |
|------|------|------|
| 上证指数 | {价格} | {%} |
| 深证成指 | {价格} | {%} |
| 创业板指 | {价格} | {%} |

## 🔥 热点板块 Top 3
（个股表格由 Agent 自动预填正宗度；Claude 负责审核覆盖，发现遗漏个股时手动补入，代码填「待查」）

## ⚠️ 人气榜隐藏信号
| 排名 | 板块 | 涨跌 | 说明 | 关注标的 |
|------|------|------|------|---------|

## 分组全景

### 一、已知强势主线
### {板块名}
- **阶段**：{stage}  **热度**：{⭐}
- **持续性**：{高/中/低}
- **支撑**：{continuation_reasons}
| 代码 | 名称 | 提及数 | 驱动 | 正宗度 | 正宗度依据 | 核心理由 |

### 二、次日发酵候选
### 三、人气先行信号（待确认）
### 四、排除项

## 盘中验证点汇总
## 扫描结论
{editorial.final_recommendations.conclusion_text}
```

---

## 置信度处理

| confidence | 处理方式 |
|-----------|---------|
| `normal` | 正常输出4分组报告 |
| `low` | 报告头部加 ⚠️ 提示，仍输出 |
| `none` | 不输出正式报告，仅输出采集失败说明 |

---

## 职责分工速查（v1.3）

| 内容 | 由谁完成 |
|------|---------|
| 时间窗口 / 采集 / 去重 / 置信度 | Python `collector/` |
| 预处理（去重/recap/catalyst）| Python `preprocessor/` |
| 板块聚类（cross-sector 权重）| Python `sector_identifier/` |
| 热度评分 / 阶段判断 / 个股提取 | Python `analysis/` |
| 双评分 / 验证点 | Python `dual_score/` |
| 4分组 / 报告草稿 | Python `output_layer/` |
| hotrank 摘要 + 关注个股推断（Node 3/4）| Agent `InfoEnrichmentAgent` |
| 补充遗漏个股（Node 9）| Agent `InfoEnrichmentAgent` |
| 正宗度判断预填（Node 5）| Agent `SemanticJudgmentAgent` |
| 板块审核备注（Node 8）| Agent `SemanticJudgmentAgent` |
| 综合结论文本（Node 7）| Agent `SemanticJudgmentAgent` |
| WebSearch 补充（agent 未覆盖时）| Claude |
| 正宗度审核与覆盖 | Claude |
| 最终报告写入 reports/*.md | Claude |
