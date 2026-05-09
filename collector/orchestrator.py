# 采集编排层
# 统一调度四个数据源，收集结果，计算置信度，输出 raw_news.json。
# 四源并行采集；GLOBAL_BUDGET 秒后强制放弃未完成的源。

import json
import threading
import time as _time
from datetime import datetime
from typing import List

from collector.models import CollectorOutput, SourceResult, NewsItem
from collector.http_client import GLOBAL_BUDGET
from collector.time_window import get_time_window
from collector.sources import (
    scrape_taoguba,
    scrape_ths_news,
    scrape_ths_hotrank,
    scrape_xueqiu,
    make_websearch_result,
)


def count_main_source_successes(results: List[SourceResult]) -> int:
    """统计主源（is_main_source=True）中抓取成功的数量"""
    return sum(1 for r in results if r.is_main_source and r.fetch_success)


def build_output(main_success_count: int,
                 results: List[SourceResult]) -> CollectorOutput:
    """
    根据主源成功数量计算置信度，合并全部条目。
    置信度规则：≥2 主源 → normal，1 主源 → low，0 主源 → none
    """
    if main_success_count >= 2:
        confidence = 'normal'
    elif main_success_count == 1:
        confidence = 'low'
    else:
        confidence = 'none'

    all_items: List[NewsItem] = []
    for r in results:
        all_items.extend(r.items)

    return CollectorOutput(
        confidence         = confidence,
        main_success_count = main_success_count,
        results            = results,
        all_items          = all_items,
    )


def run_collection(output_path: str = 'raw_news.json',
                   websearch_data: list = None) -> CollectorOutput:
    """
    执行完整采集流程并将结果写入 output_path。
    websearch_data：可选，由外部（Claude）传入的 WebSearch 结果列表。
                    传入时作为第5路补充源合并进输出，不影响置信度计算。
    返回 CollectorOutput 供调用方检查。
    """
    start, end = get_time_window()
    print(f'[采集] 时间窗口：{start.strftime("%Y-%m-%d %H:%M")} → {end.strftime("%Y-%m-%d %H:%M")}')

    tasks = [
        ('淘股吧',      lambda: scrape_taoguba(start, end)),
        ('同花顺早报',   lambda: scrape_ths_news(start, end)),
        ('同花顺人气榜', lambda: scrape_ths_hotrank()),
        ('雪球',        lambda: scrape_xueqiu(start, end)),
    ]

    results_map: dict = {}
    lock = threading.Lock()

    def _run(label, fn):
        print(f'[采集] {label} ...')
        r = fn()
        icon = '[OK]' if r.fetch_success else '[FAIL]'
        print(f'       {icon} {label}: fetch_success={r.fetch_success}, '
              f'items={r.item_count}, error={r.error_type}')
        with lock:
            results_map[label] = r

    # 四源并行启动
    threads = [
        (label, threading.Thread(target=_run, args=(label, fn), daemon=True))
        for label, fn in tasks
    ]
    t0 = _time.time()
    for _, t in threads:
        t.start()

    # 等待各线程，超过 GLOBAL_BUDGET 后放弃未完成的源
    for label, t in threads:
        remaining = max(0.0, GLOBAL_BUDGET - (_time.time() - t0))
        t.join(timeout=remaining)
        if t.is_alive():
            print(f'[警告] {label} 全流程超时，跳过')

    # 按原顺序收集结果；超时未完成的源生成失败占位
    results = []
    for label, _ in tasks:
        if label in results_map:
            results.append(results_map[label])
        else:
            results.append(SourceResult(label, True, False, [],
                                        error_type='budget_exceeded'))

    # WebSearch 补充源：不参与超时控制，不计入主源置信度
    if websearch_data is not None:
        ws_result = make_websearch_result(websearch_data)
        results.append(ws_result)
        print(f'[采集] WebSearch 补充源注入，items={ws_result.item_count}')

    output = build_output(count_main_source_successes(results), results)
    output.time_window_start = start.isoformat()

    # 序列化写入 JSON
    payload = {
        'generated_at':       datetime.now().isoformat(),
        'time_window_start':  start.isoformat(),
        'time_window_end':    end.isoformat(),
        'confidence':         output.confidence,
        'main_success_count': output.main_success_count,
        'sources': [
            {
                'name':          r.name,
                'source_type':   r.source_type,
                'is_main':       r.is_main_source,
                'fetch_success': r.fetch_success,
                'item_count':    r.item_count,
                'error_type':    r.error_type,
            }
            for r in output.results
        ],
        'items': [
            {
                'title':        item.title,
                'content':      item.content,
                'source':       item.source,
                'source_type':  item.source_type,
                'url':          item.url,
                'published_at': item.published_at,
                'heat':         item.heat,
            }
            for item in output.all_items
        ],
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f'\n[完成] 主源成功：{output.main_success_count}/4  置信度：{output.confidence}')
    print(f'[完成] {output_path} 已写入（{len(output.all_items)} 条原始数据）')

    return output
