"""
analyzer.py — 编排层总入口

输入（两条路径，优先级如下）：
  1. 列表直连（主）：由调用方传入 items 列表，采集层完成后直接传递，无 I/O 开销。
  2. 文件读取（兜底）：从 raw_news.json 读取，items 为 None 时自动启用。
输出：
  - analysis_result.json（结构化中间结果）
  - reports/YYYY-MM-DD-morning-scan.md（最终 Markdown 报告）

层级职责：
1. 编排各层管道（preprocessor → sector_identifier → analysis → dual_score → output_layer）
2. 序列化输出 analysis_result.json 与 Markdown 报告

向后兼容重导出（旧 import 路径继续有效）：
  from analyzer import compute_star_rating, compute_stage
  from analyzer import extract_stock_mentions, load_stock_names
"""

import json
import os
from dataclasses import asdict, is_dataclass

# 管道各层入口
from preprocessor.entry import preprocess
from preprocessor.report import format_summary as _pre_format
from sector_identifier.entry import identify_sectors
from sector_identifier.report import format_summary as _si_format
from analysis.entry import run_analysis_pipeline
from analysis.report import format_summary as _format_summary
from dual_score.entry import score_sectors
from dual_score.report import format_summary as _ds_format
from editorial_layer.entry import build_editorial
from output_layer.entry import build_report, build_report_from_editorial

# 向后兼容重导出：旧代码 from analyzer import X 继续有效
from preprocessor import annotate_items, deduplicate, strip_html, normalize_title
from sector_identifier import (
    is_military_false_positive, match_sectors, match_sectors_detail,
    hotrank_name_to_sector, parse_hotrank,
)
from analysis.scorer import compute_star_rating
from analysis.stage_rules import compute_stage
from analysis.entry import load_stock_names, extract_stock_mentions


def _normalize_item(item):
    if isinstance(item, dict):
        return item
    if is_dataclass(item):
        return asdict(item)
    if hasattr(item, '__dict__'):
        return vars(item)
    raise TypeError(f'Unsupported item type: {type(item)!r}')


# ── 分析管道（私有，供两条路径共用）─────────────────
def _analyze(all_items: list, confidence: str, source_stats: list,
             output_path: str = 'analysis_result.json',
             time_window_start: str = '') -> dict:
    all_items = [_normalize_item(x) for x in all_items]

    hotrank_raw = [x for x in all_items if x.get('source') == '同花顺人气榜']
    news_items  = [x for x in all_items if x.get('source') != '同花顺人气榜']

    # 预处理层
    pre_result = preprocess(news_items)
    print(_pre_format(pre_result))

    processed_items = pre_result['processed_items']
    dedup_stats = pre_result['stats']

    # 题材识别层
    si_result = identify_sectors(processed_items, hotrank_raw)
    print(_si_format(si_result))

    # 捕获 sector_item_map（sector_name → 属该板块的全量 processed_items）
    # 供 agent 层精确检索板块原文，不截断 top_items
    sector_item_map = dict(si_result.get('sector_weighted', {}))

    # 分析层
    analysis_result = run_analysis_pipeline(si_result, dedup_stats, confidence, source_stats)
    print(_format_summary(analysis_result))

    # 双评分层（接收 sectors 列表，返回增强后的 scored_sectors）
    ds_result = score_sectors(analysis_result['sectors'])
    print(_ds_format(ds_result))
    # 将双评分字段写回 analysis_result，sectors 已替换为含双评分的版本
    analysis_result['sectors']      = ds_result['scored_sectors']
    analysis_result['scoring_stats'] = ds_result['scoring_stats']

    # 日期：从 generated_at 取前 10 位（analysis_result 无独立 date 字段）
    date_str = analysis_result.get('generated_at', '')[:10] or 'unknown'

    # 写 analysis_result.json；注入时间字段供 Claude Step 3/4 读取
    if time_window_start:
        analysis_result['time_window_start'] = time_window_start
    # us_market_date：隔夜美股查询日期 = scan_date 前一个美股交易日（周一→上周五，其余→前一天）
    from editorial_layer.market_context import _prev_us_trading_day
    us_market_date = _prev_us_trading_day(date_str)
    if us_market_date:
        analysis_result['us_market_date'] = us_market_date
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    context = {
        'date':               date_str,
        'confidence':         confidence,
        'dedup_stats':        dedup_stats,
        'hotrank_signals':    analysis_result.get('hotrank_signals', []),
        'source_stats':       source_stats,
        'time_window_start':  time_window_start,  # A股上一交易日 ISO 时间，用于 WebSearch Query 1
    }

    # 编辑层：归组 + 构建个股候选 + 构建 top_sectors / hidden_signals
    editorial_result = build_editorial(analysis_result['sectors'], context)

    # agent 层：装配 state，运行两个 agent（可通过 AGENT_LAYER_ENABLED=false 禁用）
    from agent_layer import assemble_state, run_agents, write_scan_result
    state = assemble_state(
        analysis_result,
        editorial_result,
        processed_items=processed_items,
        sector_item_map=sector_item_map,
    )
    run_agents(state)                                   # 原地填充 editorial_result
    scan_dir = os.path.dirname(os.path.abspath(output_path))
    write_scan_result(state, output_dir=scan_dir)      # 写 scan_result.json

    # 输出层：消费 editorial_result → report_package + markdown + brief_markdown
    report_result = build_report_from_editorial(editorial_result)

    # 写 Markdown 报告到 reports/
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    md_path = os.path.join(report_dir, f'{date_str}-morning-scan.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(report_result['markdown'])

    # 写简报到 reports/
    brief_path = os.path.join(report_dir, f'{date_str}-morning-scan-brief.md')
    with open(brief_path, 'w', encoding='utf-8') as f:
        f.write(report_result['brief_markdown'])

    print(f'\n[完成] {len(analysis_result["sectors"])} 个板块，写入 {output_path}')
    print(f'[报告] 主报告已写入 {md_path}')
    print(f'[简报] 简报已写入  {brief_path}')

    return {**analysis_result, 'editorial_result': editorial_result, 'report_result': report_result}


# ── 分析层入口函数（公开）────────────────────────────
def run_analysis(
    items: list = None,
    confidence: str = 'unknown',
    source_stats: list = None,
    output_path: str = 'analysis_result.json',
    time_window_start: str = '',
) -> dict:
    """
    分析层对外入口。两条数据路径：

    路径 1（列表直连，主）：
      调用方传入 items 列表时直接使用，无文件 I/O。
      空列表也走此路径，不会误回退到文件读取。

    路径 2（文件读取，兜底）：
      items 为 None 时，从 raw_news.json 读取。
    """
    if items is not None:
        print(f'[分析] 数据来源：列表直连（{len(items)} 条原始 items）')
        return _analyze(items, confidence, source_stats or [], output_path,
                        time_window_start=time_window_start)

    print('[分析] 数据来源：文件读取（raw_news.json）')
    import time as _t
    try:
        mtime = os.path.getmtime('raw_news.json')
        age_min = (_t.time() - mtime) / 60
        if age_min > 30:
            raise RuntimeError(
                f'raw_news.json 已超 {age_min:.0f} 分钟未更新。'
                '请通过 pipeline.py 重新采集，或使用 run.py 启动全流程，'
                '避免对历史数据做重分析。'
            )
    except FileNotFoundError:
        raise FileNotFoundError(
            'raw_news.json 不存在。请先通过 run.py 或 pipeline.py 运行采集层。'
        )
    with open('raw_news.json', encoding='utf-8') as f:
        raw = json.load(f)
    return _analyze(
        raw.get('items', []),
        raw.get('confidence', 'unknown'),
        raw.get('sources', []),
        output_path,
        time_window_start=raw.get('time_window_start', ''),
    )


# ── 命令行入口 ────────────────────────────────────────
def main() -> None:
    run_analysis()


if __name__ == '__main__':
    main()
