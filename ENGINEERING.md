# 工程参考文档 — 早盘热点扫描 v1.3

> 本文件供开发者理解各层实现细节。日常使用只需参考 SKILL.md。

---

## 采集层（`collector/`）

| 文件 | 职责 |
|------|------|
| `entry.py` | `collect()`：加载 .env → 委托编排层 |
| `orchestrator.py` | 并行调度四源（四线程）+ WebSearch 注入 + 置信度计算 + 写 `raw_news.json` |
| `sources.py` | 各源抓取函数（失败写 `error_type`，不抛异常） |
| `market_data.py` | akshare 获取 A 股指数 + 美股关键标的（自动化，无需 WebSearch） |
| `models.py` | `NewsItem` / `SourceResult` / `CollectorOutput` |
| `time_window.py` | 上一交易日 15:00 → 今日 09:00（`chinese_calendar` 判节假日，MAX_WINDOW_DAYS=5） |
| `http_client.py` | `REQUEST_TIMEOUT=12s`，`SOURCE_BUDGET=25s`，`GLOBAL_BUDGET=90s`，1次重试 |

**四个数据源：**

| 来源 | source_type | 接入方式 | 关键技术点 |
|------|-------------|----------|-----------|
| 淘股吧 | `forum` | JSON API | 分页最多10页，热度取 `totalViewNum` |
| 同花顺早报 | `official_news` | JS 文件 | GBK 编码，手动解析非标准 JSON |
| 同花顺人气榜 | `hotrank` | HTML 表格 | GBK 编码，CSS 选择器取值 |
| 雪球 | `community` | JSON API | 需 `XUEQIU_COOKIE`；含 `$股票(代码)$` 格式 |

**置信度规则：**

| 主源成功数 | confidence |
|-----------|-----------|
| ≥ 2 | `normal` |
| 1 | `low` |
| 0 | `none` |

**常见 error_type：**
- `fetch_failed`：HTTP 请求失败
- `parse_failed`：响应体解析失败
- `budget_exceeded`：单源超时
- `no_cookie`：雪球未设置 Cookie
- `cookie_expired`：雪球 Cookie 已失效

---

## 预处理层（`preprocessor/`）

| 文件 | 职责 |
|------|------|
| `entry.py` | `preprocess(items)` → `{processed_items, stats}` |
| `rules.py` | 去重 / recap 检测 / catalyst 分类（纯函数） |
| `conclusions.py` | 对单条 item 应用规则 |
| `evidence.py` | 保留证据字段 |
| `output.py` / `report.py` / `downstream.py` | 输出构建 / 控制台摘要 / 下游字段定义 |

**去重规则（两层）：**
1. 精确去重：normalize_title（去空格/特殊字符/转小写）后 exact match
2. 包含关系去重：短标题 ≥ 8 字符 且被长标题包含 且 长/短比 < 1.6

**催化类型（6类，按优先级）：**

| 类型 | 关键词（部分） |
|------|--------------|
| `earnings` | 财报、业绩、一季报、净利润 |
| `policy` | 政策、国家队、工信部、发改委 |
| `price` | 涨价、提价、现货价、报价上调 |
| `overseas` | 美股、英伟达、台积电、纳斯达克 |
| `product` | 发布、量产、出货、新品、订单 |
| `capital` | 融资、增持、回购、北向资金 |

---

## 题材识别层（`sector_identifier/`）

| 文件 | 职责 |
|------|------|
| `entry.py` | `identify_sectors(processed_items, hotrank_raw)` → sector_result |
| `rules.py` | 板块关键词词典 / 人气榜映射表 / 军工假阳性词典 |

**9个板块及关键词（部分）：**

| 板块 | 关键词 |
|------|--------|
| 半导体 | 芯片、晶圆、存储、HBM、DRAM、集成电路、寒武纪 |
| AI算力 | GPU、服务器、液冷、CPO、光模块、算力、大模型 |
| 机器人 | 人形机器人、具身智能、减速器、丝杠、执行器 |
| 新能源 | 锂电、储能、光伏、风电、充电桩、固态电池 |
| 能源金属 | 锂矿、碳酸锂、钴价、镍价、铜矿、稀土 |
| 创新药 | 新药、临床、ADC、GLP-1、CXO、CDMO |
| 军工 | 航空发动机、无人机袭击、军费、商业航天 |
| 消费 | 白酒、餐饮、旅游、免税、电商、茅台 |
| 金融 | 券商、保险、降准、货币政策、公募基金 |

**Cross-sector 权重**：一条新闻命中 N 个板块时，对每板块贡献权重 `1/N`。

**军工假阳性过滤**：命中以色列、哈马斯、乌克兰、俄罗斯、北约等词时过滤军工归类。

---

## 分析层（`analysis/`）

| 文件 | 职责 |
|------|------|
| `entry.py` | `run_analysis_pipeline()` 编排；`build_sector_summaries()`；`extract_stock_mentions()`；`build_hotrank_only()` |
| `scorer.py` | `compute_star_rating()` → 1-5 星 |
| `stage_rules.py` | `apply_stage_rules()` → (stage_label, stage_signals) |

**热度评分规则：**

| ⭐ | 条件 |
|----|------|
| ⭐⭐⭐⭐⭐ | src ≥ 3 且 hotrank ≤ 3 且 eff ≥ 8 |
| ⭐⭐⭐⭐ | src ≥ 2 且 hotrank ≤ 10；或 src ≥ 2 且 eff ≥ 8 |
| ⭐⭐⭐ | src ≥ 2；或 eff ≥ 5 |
| ⭐⭐ | eff ≥ 2 |
| ⭐ | hotrank_only 补建 |

**四阶段判断（优先级从高到低）：**

| 阶段 | 条件 |
|------|------|
| `已高潮` | src ≥ 3 且 eff ≥ 6 且 recap ≥ 0.50 |
| `发酵中`（人气榜） | hotrank ≤ 10 且 eff ≥ 4 且 recap < 0.50 |
| `发酵中`（新闻量） | src ≥ 2 且 eff ≥ 6 且 new_cat ≥ 1 且 recap < 0.50 |
| `预发酵` | 人气先行或 hotrank ≤ 5 单源，且有新催化 |
| `unknown` | 以上均不满足 |

**个股提取（两路，含跨板块过滤）：**
1. 雪球格式：正则匹配 `$股票名(SH/SZ/BJ+代码)$`
2. 词典匹配：`stocks_dict.csv` 5246条全量A股名称匹配
- **v1.3 修复**：提取前过滤 `_weight >= 0.5` 的帖子（主要属于本板块），防止跨板块综述帖将同一批个股"复制"到多个板块；fallback 保证不为空。

---

## 双评分层（`dual_score/`）

| 文件 | 职责 |
|------|------|
| `entry.py` | `score_sectors()` → 调用 continuation + fermentation |
| `continuation.py` | `score_continuation()` → `{score, reasons, risks}` |
| `fermentation.py` | `score_fermentation()` → `{score, reasons, trigger_points}` |

**持续性评分（`score_continuation()`）：**

| 分级 | 条件 |
|------|------|
| `高` | 活跃阶段 且 催化密度 ≥ 0.30 且 recap < 0.40 |
| `中` | 活跃阶段 且 (新催化 OR multi_source) 且 recap < 0.60 |
| `低` | 其余 |

**发酵评分（`score_fermentation()`）：**

| 分级 | 条件 |
|------|------|
| `高` | 早期阶段 且 有新催化 且 人气先行 |
| `中` | 早期阶段 且 (新催化 OR hotrank ≤ 10) 且 recap < 0.50 |
| `低` | 其余 |

---

## 编辑层（`editorial_layer/`）

| 文件 | 职责 |
|------|------|
| `entry.py` | `build_editorial()` → editorial_result（含 None 占位字段） |
| `stock_merger.py` | `merge_stock_candidates()` → stock_candidates 列表 |
| `sector_builder.py` | `build_top_sectors()` / `build_hidden_signals()` |
| `market_context.py` | `build_market_context()`（akshare 填充 A股/美股数据） |
| `recommendations.py` | `build_final_recommendations()` |
| `report_package.py` | `build_report_package()` |

---

## 输出层（`output_layer/`）

| 文件 | 职责 |
|------|------|
| `entry.py` | `build_report_from_editorial()` → 生成 Markdown 草稿 |
| `rules.py` | `classify_group()` → 4分组归类规则 |
| `report.py` | `build_markdown()` → 完整 Markdown 字符串 |

**4分组规则（优先级从高到低）：**

| 栏目 | 归入条件 |
|------|---------|
| 已知强势主线 | stage ∈ {已高潮, 发酵中} 且 continuation ∈ {高, 中} |
| 次日发酵候选 | fermentation ∈ {高, 中} 且非"已高潮+续弱" |
| 人气先行信号 | needs_websearch=True 或 hotrank ≤ 10 且 eff < 2 |
| 排除项 | 兜底 |

---

## Agent 层（`agent_layer/`）

| 文件 | 职责 |
|------|------|
| `state.py` | `ScanState` + `assemble_state()` |
| `config.py` | `AgentConfig`：从 .env 加载 provider / model / key |
| `entry.py` | `run_agents()` 主编排 + `write_scan_result()` |
| `provider/` | `BaseProvider` / `AnthropicProvider` / `OpenAIProvider` / `factory` |
| `agents/info_enrichment.py` | Node 3（hotrank摘要）+ Node 4（关注个股）+ Node 9（补充个股） |
| `agents/semantic_judgment.py` | Node 8（板块审核）+ Node 5（正宗度）+ Node 7（结论） |
| `prompts/*.txt` | 6个提示词，可直接编辑热更新 |

**Agent 写入字段（仅在 `scan_result.json` 中）：**

| 字段路径 | 写入节点 |
|---------|---------|
| `editorial.hidden_signals[i].websearch_summary` | Node 3 |
| `editorial.hidden_signals[i].focus_stocks` | Node 4 |
| `editorial.all_sectors[i].stock_candidates`（APPEND） | Node 9 |
| `editorial.all_sectors[i].stock_candidates[j].authenticity/evidence/reason` | Node 5 |
| `editorial.all_sectors[i].agent_review` | Node 8 |
| `editorial.final_recommendations.conclusion_text` | Node 7 |

**费用控制（`config/agent_config.json`）：**
- `max_llm_calls_per_run`：默认 40，超出后警告但不强制中断
- 各节点 `enabled` 开关可独立关闭

---

## `analysis_result.json` 结构（v1.2，不含 agent 数据）

```json
{
  "generated_at": "ISO时间戳",
  "time_window_start": "2026-05-08T15:00:00",
  "confidence": "normal",
  "sectors": [
    {
      "name": "半导体",
      "star_rating": 4,
      "stage": "发酵中",
      "effective_count": 10.3,
      "source_count": 2,
      "hotrank": {"rank": 1, "name": "半导体", "change_pct": 3.37},
      "stock_mentions": [{"name": "海光信息", "code": "688041", "mention_count": 2}],
      "continuation_score": "高",
      "fermentation_score": "中",
      "trigger_points": ["若开盘连续涨停则确认发酵"]
    }
  ],
  "hotrank_signals": [
    {"rank": 1, "hotrank_name": "半导体", "signal_type": "news_driven"}
  ]
}
```

## `scan_result.json` 结构（v1.3，含 agent 数据）

```json
{
  "meta": {
    "scan_date": "2026-05-09",
    "agent_enabled": true,
    "agent_calls_made": 32,
    "agent_duration_sec": 58
  },
  "editorial": {
    "all_sectors": [
      {
        "name": "半导体",
        "stock_candidates": [
          {
            "name": "海光信息", "code": "688041",
            "authenticity": "核心股",
            "authenticity_evidence": "主营国产CPU，占收入>90%",
            "core_reason": "国产CPU龙头，核心受益"
          }
        ],
        "agent_review": {"note": "信号真实，催化有效", "confidence": "high"}
      }
    ],
    "hidden_signals": [
      {
        "hotrank_name": "军工装备",
        "websearch_summary": "军费预算增长催化...",
        "focus_stocks": "600760 中航沈飞、600893 航发动力"
      }
    ],
    "final_recommendations": {
      "conclusion_text": "半导体作为主线，建议持有..."
    }
  }
}
```
