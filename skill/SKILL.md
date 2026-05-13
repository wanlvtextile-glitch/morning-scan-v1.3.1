---
name: market-morning-scan
description: 早盘扫描项目的本地维护说明，描述当前正式运行链路、关键输入输出和人工复核关注点。
---

# Market Morning Scan

## Current Runtime Model

The project now runs on a single primary data model:

- `processed_items`
- `logic_units`
- `signal_stats`
- `dedup_decisions`
- `core_logic_units`
- `stock_branches`

## Main Entry

```bash
python cli.py run
```

## Main Outputs

- `raw_news.json`
- `analysis_result.json`
- `YYYY-MM-DD-scan_result.json`
- `reports/YYYY-MM-DD-morning-scan.md`
- `reports/YYYY-MM-DD-morning-scan-brief.md`

## Review Focus

- whether main sectors are supported by coherent `core_logic_units`
- whether stock candidates are derived from meaningful `stock_branches`
- whether stage and score labels match the logic summaries
- whether `hotrank_only` signals are rendered only through `hidden_signals`
- whether final report avoids pseudo stock names, repeated sector payloads, and noisy raw clue sentences

## Hotrank Semantics

- treat `source_type == 'hotrank'` as the stable identifier for 同花顺人气榜 items
- keep `hotrank_signals` as the upstream signal list and `hidden_signals` as the report-facing hotrank-only subset
- do not reintroduce a standalone `人气先行信号` report group; hotrank-only observations belong in `人气榜隐藏信号`
- keep `final_recommendations.watch_list` as a compatibility field, but allow it to stay empty when no standalone hotrank group exists

## Report Integrity Checks

- stock tables must contain real stock candidates, not title fragments, institution tags, or sentence-shaped noise
- sector-specific content must not be reused across unrelated sectors unless there is an explicit shared `logic_unit`
- `logic_summary` should prefer cleaned summaries over raw source phrasing when source text is conversational or盘面化

## Stock Entity Rules

- derive final stock candidates from validated `stock_branches`, not directly from raw titles or loose regex hits
- reject sentence-shaped fragments such as action phrases, market narration, or long descriptive clauses even if they contain a company-like token
- reject institution or research-label entities such as broker team names and report headers
- preserve a legitimate single-stock branch when the entity itself is valid, even if sector aggregation is still sparse
- keep stock name and stock code aligned with the A-share dictionary path; if the name cannot be resolved into a valid stock entity, it must not enter the final table

## Architecture Invariants

- `pipeline.py` is the single coordinator for all file I/O; domain layers must not write files
- `analyzer._analyze()` computes and returns paths/payloads; `pipeline.py` does the actual writes
- `collector/orchestrator.run_collection()` returns `CollectorOutput` with no file side effects; `pipeline.py` calls `_write_raw_news()` separately
- `output_layer.entry` exposes only `build_report_from_editorial`; the old `build_report` interface has been removed
- dead imports in domain modules should be cleaned up; use `tests/test_dead_import_cleanup.py` as the regression guard

## Data Sources

All five sources perform real-time network fetches on each run. No historical cache is used.

| Source | Type | Auth |
|---|---|---|
| 淘股吧 | HTTP API, paginated | none |
| 同花顺早报 | JS file, GBK encoding | none |
| 同花顺人气榜 | HTML table scrape | none |
| 雪球 | JSON API, paginated | `XUEQIU_COOKIE` in `.env` |
| 知识星球 (ZSXQ) | REST API, paginated | `ZSXQ_TOPICS_CURL` or individual `ZSXQ_*` env vars in `.env` |

Time window: previous A-share trading day 15:00 → today 09:00 (computed by `collector/time_window.py` using `chinese_calendar`). Maximum window capped at 5 days to handle long holidays.

ZSXQ item count reflects actual posts within the window for the configured `group_id`; lower counts overnight are expected behavior, not a bug.

## Test Suite

51 regression tests cover:
- pipeline file I/O invariants (`test_pipeline_mirror_regression`)
- collector no-file-side-effect contract (`test_collector_no_file_side_effect_regression`)
- analyzer no-file-side-effect contract (`test_analyzer_no_file_side_effect_regression`)
- output layer single-interface contract (`test_output_layer_single_interface_regression`)
- dead import cleanup guard (`test_dead_import_cleanup`)
- sector logic, hotrank routing, stock entity filtering, report rendering

Run with: `python -m pytest tests/ -v`

## Known External Risks

- US market proxy failures can still break overseas market snapshots
- upstream source counts can change run to run
- LLM output quality still depends on provider stability

## Maintenance Rule

Future changes should extend the logic-unit path, not reintroduce historical compatibility shortcuts.
