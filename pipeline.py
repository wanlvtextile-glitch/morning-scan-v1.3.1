import json
import os
import shutil
import sys
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from analyzer import run_analysis
from checks import assert_ready
from collector import collect


def _sep(title: str = ''):
    line = '=' * 60
    print(f'\n{line}')
    if title:
        print(f'  {title}')
        print(line)


def _build_run_paths(project_root: str) -> dict:
    run_stamp = datetime.now().strftime('%Y-%m-%dT%H%M%S')
    run_dir = os.path.join(project_root, 'runs', run_stamp)
    report_dir = os.path.join(run_dir, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    return {
        'run_dir': run_dir,
        'report_dir': report_dir,
        'raw_news': os.path.join(run_dir, 'raw_news.json'),
        'analysis_result': os.path.join(run_dir, 'analysis_result.json'),
    }


def _write_raw_news(collector_output, path: str) -> None:
    payload = {
        'generated_at': datetime.now().isoformat(),
        'time_window_start': collector_output.time_window_start,
        'time_window_end': collector_output.time_window_end,
        'confidence': collector_output.confidence,
        'main_success_count': collector_output.main_success_count,
        'main_source_total': collector_output.main_source_total,
        'sources': [
            {
                'name': r.name,
                'source_type': r.source_type,
                'is_main': r.is_main_source,
                'fetch_success': r.fetch_success,
                'item_count': r.item_count,
                'error_type': r.error_type,
            }
            for r in collector_output.results
        ],
        'items': [
            {
                'title': item.title,
                'content': item.content,
                'source': item.source,
                'source_type': item.source_type,
                'url': item.url,
                'published_at': item.published_at,
                'heat': item.heat,
            }
            for item in collector_output.all_items
        ],
    }
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'[采集] raw_news.json 写入 {len(collector_output.all_items)} 条，路径：{path}')


def _mirror_latest(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    shutil.copyfile(src, dst)


def _build_source_stats(collector_output) -> list:
    return [
        {
            'name': r.name,
            'source_type': r.source_type,
            'is_main': r.is_main_source,
            'fetch_success': r.fetch_success,
            'item_count': r.item_count,
            'error_type': r.error_type,
        }
        for r in collector_output.results
    ]


def _print_handoff(collector_output, analysis_result: dict):
    editorial = analysis_result.get('editorial_result', {})
    sectors = editorial.get('all_sectors', analysis_result.get('sectors', []))
    confidence = collector_output.confidence
    date_str = analysis_result.get('generated_at', '')[:10] or 'unknown'

    _sep('Pipeline Handoff')

    print(
        f'主源成功：{collector_output.main_success_count}/{collector_output.main_source_total}  '
        f'置信度：{confidence}  '
        f'总条数：{len(collector_output.all_items)}'
    )
    for r in collector_output.results:
        icon = '[OK]' if r.fetch_success else '[FAIL]'
        extra = f' ({r.error_type})' if r.error_type else ''
        print(f'  {icon} {r.name}  {r.item_count} 条{extra}')

    print(f'\n板块数：{len(sectors)}')
    print('输出物：')
    print('  raw_news.json / analysis_result.json / YYYY-MM-DD-scan_result.json')
    if date_str:
        print(f'  reports/{date_str}-morning-scan.md')
        print(f'  reports/{date_str}-morning-scan-brief.md')


def run_pipeline() -> dict:
    assert_ready()

    project_root = os.path.dirname(os.path.abspath(__file__))
    paths = _build_run_paths(project_root)

    _sep('Step 1 采集')
    collector_output = collect()
    _write_raw_news(collector_output, paths['raw_news'])
    _mirror_latest(paths['raw_news'], os.path.join(project_root, 'raw_news.json'))

    source_stats = _build_source_stats(collector_output)

    _sep('Step 2 分析')
    analysis_result = run_analysis(
        items=collector_output.all_items,
        confidence=collector_output.confidence,
        source_stats=source_stats,
        output_path=paths['analysis_result'],
        time_window_start=collector_output.time_window_start,
        report_dir=paths['report_dir'],
    )

    date_str = analysis_result.get('generated_at', '')[:10] or 'unknown'

    with open(analysis_result['analysis_result_path'], 'w', encoding='utf-8') as f:
        json.dump(analysis_result['analysis_json_payload'], f, ensure_ascii=False, indent=2)
    print(f'[分析] analysis_result.json 写入 {analysis_result["analysis_result_path"]}')

    os.makedirs(paths['report_dir'], exist_ok=True)
    with open(analysis_result['report_markdown_path'], 'w', encoding='utf-8') as f:
        f.write(analysis_result['report_result']['markdown'])
    with open(analysis_result['report_brief_path'], 'w', encoding='utf-8') as f:
        f.write(analysis_result['report_result']['brief_markdown'])
    print(f'[报告] 主报告写入 {analysis_result["report_markdown_path"]}')
    print(f'[报告] 简报写入 {analysis_result["report_brief_path"]}')

    _mirror_latest(analysis_result['analysis_result_path'], os.path.join(project_root, 'analysis_result.json'))
    _mirror_latest(analysis_result['scan_result_path'], os.path.join(project_root, f'{date_str}-scan_result.json'))
    _mirror_latest(analysis_result['report_markdown_path'], os.path.join(project_root, 'reports', f'{date_str}-morning-scan.md'))
    _mirror_latest(analysis_result['report_brief_path'], os.path.join(project_root, 'reports', f'{date_str}-morning-scan-brief.md'))

    _print_handoff(collector_output, analysis_result)
    return analysis_result


if __name__ == '__main__':
    run_pipeline()
