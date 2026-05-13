# Morning-Scan Runtime Rules

## 目标

确保 `morning-scan` 的最终交付始终是：
- 采集层
- 分析层
- Agent / LLM 参与
- 最终 Markdown 报告

而不是中途降级成仅 Python 结果。

## 当前运行规则

### 1. 启动即校验，不满足就阻断

`python cli.py run` / `pipeline.run_pipeline()` 会先执行 `checks.assert_ready()`。

以下任一不满足，都必须直接停止：
- `.env` 不存在
- `AGENT_LAYER_ENABLED != true`
- `LLM_PROVIDER` 未填
- `LLM_MODEL` 未填
- 对应的 LLM API Key / Base URL 未填
- `XUEQIU_COOKIE` 未填
- `ZSXQ` 主源请求头未填完整

### 2. ZSXQ 作为主源

当前主源集合：
- 淘股吧
- 同花顺新闻
- 同花顺人气榜
- 雪球
- ZSXQ

`twitter` / `telegram` 当前先关闭，仅保留未来扩展位置。

### 3. 禁止 Agent 静默降级

旧逻辑里：
- Agent 关掉
- 或 API Key 缺失
- 仍会继续往下跑

当前已改成：
- 直接抛错
- 不生成最终 morning-scan 报告

### 4. 禁止分析层文件兜底

旧逻辑允许：
- `analyzer.py` 直接读 `raw_news.json`

当前已改成：
- `run_analysis()` 必须显式接收 collector 内存数据
- 禁止再从 `raw_news.json` 兜底补数据

## 产物策略

### 每次运行落盘

当前产物按次归档到：

```text
runs/<timestamp>/
```

包含：
- `raw_news.json`
- `analysis_result.json`
- `YYYY-MM-DD-scan_result.json`
- `reports/YYYY-MM-DD-morning-scan.md`
- `reports/YYYY-MM-DD-morning-scan-brief.md`

### latest 镜像

为了兼容现有读取路径，根目录仍保留：
- `raw_news.json`
- `analysis_result.json`
- `YYYY-MM-DD-scan_result.json`
- `reports/...`

这些是最近一次运行的镜像，不是唯一归档。

## 报告链路约束

### 1. 人气榜链路

- 人气榜识别以 `source_type='hotrank'` 为准，不依赖 `source` 文案名硬编码。
- `hotrank_signals` 是分析层全量人气信号。
- `hidden_signals` 只承接 `signal_type='hotrank_only'`，用于最终报告中的 `人气榜隐藏信号` 段。
- 不再保留单独的 `人气先行信号` 分组；如果后续出现同类需求，优先检查是否只是隐藏信号展示问题。

### 2. 报告实体质量

- `stock_candidates` 必须来自有效的 `stock_branches`，不能回退为标题片段、机构名或整句盘面描述。
- `logic_summary` 优先输出清洗后的逻辑摘要；原始标题仅在可读且无噪声时使用。
- 不同板块的候选股和逻辑线索不能因为复用同一批中间结果而大面积重复。

### 3. 股票代码与名称识别

- 股票实体进入最终表前，必须先通过名称级有效性校验，再与股票字典完成代码映射。
- 仅“像公司名”但实际属于句子片段、机构标签、研报抬头的文本，不能生成股票代码，也不能进入最终候选。
- 合法的单只股票分支不能因为题材聚合条数偏少而被误删。
- 如果名称无法稳定映射到有效股票实体，应直接丢弃，而不是保留空代码或伪代码候选。

## 待处理

### 1. confidence 规则

当前仍是旧阈值：
- 主源成功数 `>= 2` -> `normal`
- `== 1` -> `low`
- 否则 -> `none`

后续需要改成和动态主源数量一致的规则。

### 2. CI / 测试 / 部署自动化

后续维护建议见：

```text
MORNING_SCAN_PENDING_MAINTENANCE.md
```
