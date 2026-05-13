# 使用说明

## 这是什么

这是一个运行在 Claude Code 中的早盘扫描工具。触发后会自动完成：

1. 采集五路主源资讯
2. 识别热点板块
3. 评估板块热度、阶段、持续性和发酵概率
4. 生成候选个股与正宗度判断
5. 输出主报告、简报和结构化结果

## 安装

```bash
pip install -r requirements.txt
cp .env.example .env
```

然后填写 `.env`：

- `XUEQIU_COOKIE`
- `AGENT_LAYER_ENABLED=true`
- `LLM_PROVIDER`
- `LLM_MODEL`
- 对应的 API Key / Base URL

## 验证

```bash
python cli.py check
python cli.py doctor
python -m unittest discover -s tests
```

## 运行

命令行：

```bash
python cli.py run
```

Claude Code 对话触发词：

```text
启动早盘扫描
早盘热点
扫描市场
```

## 当前数据源

- 淘股吧
- 同花顺早报
- 同花顺人气榜
- 雪球
- ZSXQ

## 输出

每次运行都会写入：

```text
runs/<timestamp>/
```

包含：

- `raw_news.json`
- `analysis_result.json`
- `YYYY-MM-DD-scan_result.json`
- `reports/YYYY-MM-DD-morning-scan.md`
- `reports/YYYY-MM-DD-morning-scan-brief.md`

## 当前运行规则

- 启动前必须通过环境校验。
- Agent 层未就绪时，流程直接中止，不再静默降级。
- 分析层必须显式消费采集结果，不允许再从 `raw_news.json` 兜底补数。
- 人气榜识别以 `source_type='hotrank'` 为准，不依赖 `source` 文案硬编码。

## 报告规则

- `hotrank_signals` 是分析层全量人气信号。
- `hidden_signals` 是报告层承接的 `hotrank_only` 子集。
- 最终报告保留 `人气榜隐藏信号`，不再保留独立 `人气先行信号` 分组。
- `stock_candidates` 必须是有效股票实体，不能是标题片段、机构名或盘面句子。
- 不同板块不能因为中间结果复用而出现大面积相同数据。
- `logic_summary` 优先使用清洗后的摘要，而不是原始噪声标题。

股票识别补充规则：

- 名称先过实体过滤，再映射股票代码。
- 机构名、研报标签、句子型片段不会进入最终个股表。
- 合法单股分支即使样本少也应保留。
- 名称无法稳定映射到股票字典时，直接丢弃，不保留伪候选。

## 常见问题

**雪球 0 条或 Cookie 过期**

更新 `XUEQIU_COOKIE`。

**Agent 层失败**

优先检查 `.env` 中的 LLM 配置；当前不会自动降级继续跑。

**美股 ProxyError**

通常是外部网络或代理问题，不影响 A 股报告主链路。
