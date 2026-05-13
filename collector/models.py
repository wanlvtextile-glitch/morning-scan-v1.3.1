from dataclasses import dataclass, field
from typing import List, Optional

SOURCE_TYPES: dict = {
    '淘股吧': 'forum',
    '同花顺早报': 'official_news',
    '同花顺人气榜': 'hotrank',
    '雪球': 'community',
    'Twitter': 'social_kol',
    'Telegram': 'social_channel',
    'ZSXQ': 'paid_research',
    'WebSearch': 'supplement',
}


@dataclass
class NewsItem:
    title: str
    content: str
    source: str
    url: str
    published_at: str
    heat: int = 0
    source_type: str = field(default='')

    def __post_init__(self):
        if not self.source_type:
            self.source_type = SOURCE_TYPES.get(self.source, 'unknown')


@dataclass
class SourceResult:
    name: str
    is_main_source: bool
    fetch_success: bool
    items: List[NewsItem]
    item_count: int = 0
    error_type: Optional[str] = None
    source_type: str = field(default='')

    def __post_init__(self):
        if not self.source_type:
            self.source_type = SOURCE_TYPES.get(self.name, 'unknown')


@dataclass
class CollectorOutput:
    confidence: str
    main_success_count: int
    main_source_total: int
    results: List[SourceResult]
    all_items: List[NewsItem]
    time_window_start: str = ''
    time_window_end: str = ''
