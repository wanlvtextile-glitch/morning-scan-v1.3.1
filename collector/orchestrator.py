from concurrent.futures import ThreadPoolExecutor, wait
from typing import List

from collector.http_client import GLOBAL_BUDGET
from collector.models import CollectorOutput, NewsItem, SourceResult
from collector.registry import RUNTIME_INJECTED, get_enabled_sources
from collector.time_window import get_time_window


def count_main_source_successes(results: List[SourceResult]) -> int:
    return sum(1 for r in results if r.is_main_source and r.fetch_success)


def build_output(main_success_count: int, results: List[SourceResult]) -> CollectorOutput:
    if main_success_count >= 2:
        confidence = 'normal'
    elif main_success_count == 1:
        confidence = 'low'
    else:
        confidence = 'none'

    all_items: List[NewsItem] = []
    for result in results:
        all_items.extend(result.items)

    return CollectorOutput(
        confidence=confidence,
        main_success_count=main_success_count,
        main_source_total=sum(1 for r in results if r.is_main_source),
        results=results,
        all_items=all_items,
    )


def _collect_one_source(source_def, start, end):
    print(f'[采集] {source_def.name} ...')
    result = source_def.collect(start=start, end=end)
    icon = '[OK]' if result.fetch_success else '[FAIL]'
    print(
        f'       {icon} {source_def.name}: '
        f'fetch_success={result.fetch_success}, items={result.item_count}, error={result.error_type}'
    )
    return result


def run_collection(websearch_data: list = None) -> CollectorOutput:
    start, end = get_time_window()
    print(f'[采集] 时间窗口：{start.strftime("%Y-%m-%d %H:%M")} -> {end.strftime("%Y-%m-%d %H:%M")}')

    sources = get_enabled_sources()
    threaded_sources = [s for s in sources if s.runtime_mode != RUNTIME_INJECTED]
    injected_sources = [s for s in sources if s.runtime_mode == RUNTIME_INJECTED]

    results_map: dict = {}

    with ThreadPoolExecutor(max_workers=max(1, len(threaded_sources))) as executor:
        future_map = {
            executor.submit(_collect_one_source, source_def, start, end): source_def
            for source_def in threaded_sources
        }
        done, not_done = wait(future_map.keys(), timeout=GLOBAL_BUDGET)

        for future in done:
            source_def = future_map[future]
            try:
                results_map[source_def.key] = future.result()
            except Exception as exc:
                print(f'[异常] {source_def.name} 运行失败：{exc}')
                results_map[source_def.key] = SourceResult(
                    name=source_def.name,
                    is_main_source=source_def.is_main_source,
                    fetch_success=False,
                    items=[],
                    error_type='runtime_exception',
                    source_type=source_def.source_type,
                )

        for future in not_done:
            source_def = future_map[future]
            print(f'[预算] {source_def.name} 超出全局预算，标记为 budget_exceeded')
            results_map[source_def.key] = source_def.build_budget_exceeded_result()

        executor.shutdown(wait=False, cancel_futures=True)

    results: List[SourceResult] = []
    for source_def in threaded_sources:
        results.append(results_map.get(source_def.key, source_def.build_budget_exceeded_result()))

    for source_def in injected_sources:
        if websearch_data is None:
            continue
        injected_result = source_def.collect(injected_items=websearch_data)
        results.append(injected_result)
        print(f'[采集] {source_def.name} 注入完成：items={injected_result.item_count}')

    output = build_output(count_main_source_successes(results), results)
    output.time_window_start = start.isoformat()
    output.time_window_end = end.isoformat()

    print(
        f'\n[完成] 主源成功：{output.main_success_count}/{output.main_source_total} 置信度：{output.confidence}'
    )
    print(f'[完成] 采集 {len(output.all_items)} 条内容')
    return output
