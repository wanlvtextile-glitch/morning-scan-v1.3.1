# 数据结构层
# 定义采集层的全部数据类型，供各模块共享使用。
# 不包含任何业务逻辑，只做字段定义和 source_type 自动推导。

from dataclasses import dataclass, field
from typing import Optional, List

# 来源类型映射：标注每条数据的来源性质，供分析层区分信号权重
SOURCE_TYPES: dict = {
    '淘股吧':       'forum',          # 论坛热帖：情绪信号，覆盖面广但噪声高
    '同花顺早报':   'official_news',  # 官方资讯：权威性高，信号偏滞后
    '同花顺人气榜': 'hotrank',        # 人气榜：价格驱动的板块排名，先行指标
    '雪球':         'community',      # 投资社区：兼具讨论与结构化股票数据
    'WebSearch':    'supplement',     # 补充源：隔夜联动与市场背景，由 Claude 执行后注入
}


@dataclass
class NewsItem:
    """单条新闻 / 帖子 / 榜单数据"""
    title: str
    content: str
    source: str
    url: str
    published_at: str
    heat: int = 0
    source_type: str = field(default='')

    def __post_init__(self):
        # source_type 从 source 自动推导；显式传入时不覆盖（方便测试 mock）
        if not self.source_type:
            self.source_type = SOURCE_TYPES.get(self.source, 'unknown')


@dataclass
class SourceResult:
    """单个数据源的采集结果"""
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
    """全部来源合并后的采集输出"""
    confidence: str            # 'normal' | 'low' | 'none'
    main_success_count: int
    results: List[SourceResult]
    all_items: List[NewsItem]  # 原始未去重数据，去重在分析层进行
    time_window_start: str = ''  # A股上一交易日 ISO 时间（如 2026-04-30T15:00:00）
