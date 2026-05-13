import os
from dataclasses import asdict, is_dataclass
from typing import Optional

from analysis.entry import run_analysis_pipeline
from analysis.report import format_summary as _format_summary
from dual_score.entry import score_sectors
from dual_score.report import format_summary as _ds_format
from editorial_layer.entry import build_editorial
from output_layer.entry import build_report_from_editorial
from preprocessor.entry import preprocess
from preprocessor.report import format_summary as _pre_format
from sector_identifier.entry import identify_sectors
from sector_identifier.report import format_summary as _si_format


def _normalize_item(item):
    if isinstance(item, dict):
        return item
    if is_dataclass(item):
        return asdict(item)
    if hasattr(item, '__dict__'):
        return vars(item)
    raise TypeError(f'Unsupported item type: {type(item)!r}')


def _split_hotrank_items(all_items: list[dict]) -> tuple[list[dict], list[dict]]:
    hotrank_items: list[dict] = []
    news_items: list[dict] = []

    for item in all_items:
        source_type = item.get('source_type')
        source_name = item.get('source')
        if source_type == 'hotrank' or source_name == '同花顺人气榜':
            hotrank_items.append(item)
        else:
            news_items.append(item)

    return hotrank_items, news_items


def _analyze(
    all_items: list,
    confidence: str,
    source_stats: list,
    output_path: str = 'analysis_result.json',
    time_window_start: str = '',
    report_dir: Optional[str] = None,
) -> dict:
    all_items = [_normalize_item(x) for x in all_items]

    hotrank_raw, news_items = _split_hotrank_items(all_items)

    pre_result = preprocess(news_items)
    print(_pre_format(pre_result))

    processed_items = pre_result['processed_items']
    dedup_stats = pre_result['stats']
    logic_units = pre_result.get('logic_units', [])
    signal_stats = pre_result.get('signal_stats', {})
    dedup_decisions = pre_result.get('dedup_decisions', [])

    si_result = identify_sectors(processed_items, hotrank_raw)
    print(_si_format(si_result))
    analysis_result = run_analysis_pipeline(
        si_result,
        dedup_stats,
        confidence,
        source_stats,
        preprocess_context={
            'processed_items': processed_items,
            'logic_units': logic_units,
            'signal_stats': signal_stats,
            'dedup_decisions': dedup_decisions,
        },
    )
    print(_format_summary(analysis_result))

    ds_result = score_sectors(analysis_result['sectors'])
    print(_ds_format(ds_result))
    analysis_result['sectors'] = ds_result['scored_sectors']
    analysis_result['scoring_stats'] = ds_result['scoring_stats']

    date_str = analysis_result.get('generated_at', '')[:10] or 'unknown'
    if time_window_start:
        analysis_result['time_window_start'] = time_window_start

    from editorial_layer.market_context import _prev_us_trading_day

    us_market_date = _prev_us_trading_day(date_str)
    if us_market_date:
        analysis_result['us_market_date'] = us_market_date

    analysis_json_payload = dict(analysis_result)

    context = {
        'date': date_str,
        'confidence': confidence,
        'dedup_stats': dedup_stats,
        'preprocess_signal_stats': signal_stats,
        'hotrank_signals': analysis_result.get('hotrank_signals', []),
        'source_stats': source_stats,
        'time_window_start': time_window_start,
    }

    editorial_result = build_editorial(analysis_result['sectors'], context)

    from agents import assemble_state, run_agents, write_scan_result

    state = assemble_state(
        analysis_result,
        editorial_result,
        processed_items=processed_items,
        logic_units=logic_units,
        signal_stats=signal_stats,
        dedup_decisions=dedup_decisions,
    )
    run_agents(state)
    scan_dir = os.path.dirname(os.path.abspath(output_path))
    scan_result_path = write_scan_result(state, output_dir=scan_dir)

    report_result = build_report_from_editorial(editorial_result)

    if report_dir is None:
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')

    md_path = os.path.join(report_dir, f'{date_str}-morning-scan.md')
    brief_path = os.path.join(report_dir, f'{date_str}-morning-scan-brief.md')

    print(f'\n[完成] {len(analysis_result["sectors"])} 个板块')

    return {
        **analysis_result,
        'editorial_result': editorial_result,
        'report_result': report_result,
        'scan_result_path': scan_result_path,
        'analysis_result_path': output_path,
        'analysis_json_payload': analysis_json_payload,
        'report_markdown_path': md_path,
        'report_brief_path': brief_path,
    }


def run_analysis(
    items: list = None,
    confidence: str = 'unknown',
    source_stats: list = None,
    output_path: str = 'analysis_result.json',
    time_window_start: str = '',
    report_dir: Optional[str] = None,
) -> dict:
    if items is None:
        raise RuntimeError(
            'analysis 层的文件兜底模式已禁用。'
            '请通过 pipeline.py / cli.py run 先执行采集，并把 collector_output.all_items 直接传入分析层。'
        )

    print(f'[分析] 数据来源：内存输入，共 {len(items)} 条')
    return _analyze(
        items,
        confidence,
        source_stats or [],
        output_path,
        time_window_start=time_window_start,
        report_dir=report_dir,
    )


def main() -> None:
    raise RuntimeError('禁止直接以文件兜底方式运行 analyzer.py。请改用 python cli.py run。')


if __name__ == '__main__':
    main()
