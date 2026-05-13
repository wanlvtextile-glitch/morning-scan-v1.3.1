import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

from collector.models import SourceResult
from collector.social_sources import scrape_telegram, scrape_twitter
from collector.sources import (
    make_websearch_result,
    scrape_taoguba,
    scrape_ths_hotrank,
    scrape_ths_news,
    scrape_xueqiu,
)
from collector.zsxq_source import scrape_zsxq

RegistryHandler = Callable[..., SourceResult]

RUNTIME_THREADED = 'threaded'
RUNTIME_INJECTED = 'injected'

DEFAULT_REGISTRY_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'config', 'source_registry.json')
)


@dataclass
class SourceDefinition:
    key: str
    name: str
    source_type: str
    is_main_source: bool
    handler: RegistryHandler
    runtime_mode: str = RUNTIME_THREADED
    enabled: bool = True
    passes_time_window: bool = True

    def collect(self,
                start: Optional[datetime] = None,
                end: Optional[datetime] = None,
                injected_items: Optional[list] = None) -> SourceResult:
        if self.runtime_mode == RUNTIME_INJECTED:
            result = self.handler(injected_items or [])
        elif self.passes_time_window:
            result = self.handler(start, end)
        else:
            result = self.handler()
        return self._normalize_result(result)

    def build_budget_exceeded_result(self) -> SourceResult:
        return self._normalize_result(
            SourceResult(
                name=self.name,
                is_main_source=self.is_main_source,
                fetch_success=False,
                items=[],
                error_type='budget_exceeded',
                source_type=self.source_type,
            )
        )

    def _normalize_result(self, result: SourceResult) -> SourceResult:
        result.name = self.name
        result.is_main_source = self.is_main_source
        if not result.source_type or result.source_type == 'unknown':
            result.source_type = self.source_type
        for item in result.items:
            if not item.source:
                item.source = self.name
            if item.source == self.name and (
                not item.source_type or item.source_type == 'unknown'
            ):
                item.source_type = self.source_type
        result.item_count = len(result.items)
        return result


def _builtin_registry() -> dict:
    return {
        'taoguba': SourceDefinition(
            key='taoguba',
            name='淘股吧',
            source_type='forum',
            is_main_source=True,
            handler=scrape_taoguba,
        ),
        'ths_news': SourceDefinition(
            key='ths_news',
            name='同花顺早报',
            source_type='official_news',
            is_main_source=True,
            handler=scrape_ths_news,
        ),
        'ths_hotrank': SourceDefinition(
            key='ths_hotrank',
            name='同花顺人气榜',
            source_type='hotrank',
            is_main_source=True,
            handler=scrape_ths_hotrank,
            passes_time_window=False,
        ),
        'xueqiu': SourceDefinition(
            key='xueqiu',
            name='雪球',
            source_type='community',
            is_main_source=True,
            handler=scrape_xueqiu,
        ),
        'twitter': SourceDefinition(
            key='twitter',
            name='Twitter',
            source_type='social_kol',
            is_main_source=False,
            handler=scrape_twitter,
        ),
        'telegram': SourceDefinition(
            key='telegram',
            name='Telegram',
            source_type='social_channel',
            is_main_source=False,
            handler=scrape_telegram,
        ),
        'zsxq': SourceDefinition(
            key='zsxq',
            name='ZSXQ',
            source_type='paid_research',
            is_main_source=True,
            handler=scrape_zsxq,
        ),
        'websearch': SourceDefinition(
            key='websearch',
            name='WebSearch',
            source_type='supplement',
            is_main_source=False,
            handler=make_websearch_result,
            runtime_mode=RUNTIME_INJECTED,
            passes_time_window=False,
        ),
    }


def _load_registry_config(config_path: str) -> dict:
    with open(config_path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError('source_registry.json 顶层必须是对象')
    return data


def load_source_registry(config_path: str = DEFAULT_REGISTRY_PATH) -> List[SourceDefinition]:
    registry = _builtin_registry()
    if not os.path.exists(config_path):
        return list(registry.values())

    data = _load_registry_config(config_path)
    items = data.get('sources', [])
    if not isinstance(items, list):
        raise ValueError('source_registry.json 的 sources 必须是数组')

    definitions: List[SourceDefinition] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('source_registry.json 的每个 source 必须是对象')
        key = item.get('key')
        if key not in registry:
            raise ValueError(f'未知 source key: {key}')
        base = registry[key]
        definitions.append(
            SourceDefinition(
                key=base.key,
                name=base.name,
                source_type=base.source_type,
                is_main_source=base.is_main_source,
                handler=base.handler,
                runtime_mode=base.runtime_mode,
                passes_time_window=base.passes_time_window,
                enabled=item.get('enabled', True),
            )
        )

    if not definitions:
        return list(registry.values())
    return definitions


def get_enabled_sources(config_path: str = DEFAULT_REGISTRY_PATH) -> List[SourceDefinition]:
    return [source for source in load_source_registry(config_path) if source.enabled]
