# 判断规则层
# 负责：预处理层全部判断规则的常量定义和纯函数实现
# 输入：单条 item dict / item 列表
# 输出：bool / str / (list, int) 等规则结果
# 被谁调用：preprocessor/conclusions.py、preprocessor/entry.py

import re


# ── 文本工具 ──────────────────────────────────────────

def strip_html(text: str) -> str:
    """移除 HTML 标签，返回纯文本"""
    return re.sub(r'<[^>]+>', '', text or '').strip()


def normalize_title(text: str) -> str:
    """标准化标题：移除空格和非文字字符，转小写，用于去重比较"""
    return re.sub(r'[\s\W]+', '', text, flags=re.UNICODE).lower()


def make_content_preview(title: str, content: str, max_len: int = 80) -> str:
    """
    生成 content 的去冗余预览，用于下游逻辑摘要和说明文本。
    规则：
      1. content 为空或清理后不足10字符 → 返回空串
      2. content 与 title 词汇重叠比 > 60% → 返回空串
      3. 否则 → 返回 strip_html(content)[:max_len]
    目标是保留首段高信息密度内容，过滤纯重复低价值文本。
    """
    if not content:
        return ''
    c_clean = strip_html(content)
    if len(c_clean) < 10:
        return ''
    t_chars = set(normalize_title(title))
    c_chars = set(normalize_title(c_clean))
    if c_chars and len(t_chars & c_chars) / len(c_chars) > 0.6:
        return ''
    return c_clean[:max_len]


# ── 去重规则 ──────────────────────────────────────────

def deduplicate(items: list) -> tuple:
    """
    两层去重：精确去重 + 包含关系去重。
    返回 (去重后列表, 被移除数量)。
    包含关系规则：较短标题 >= 8 字符且被较长标题包含，且长/短比 < 1.6，视为重复。
    """
    seen: dict = {}
    result = []
    for item in items:
        norm = normalize_title(item.get('title', ''))
        if len(norm) < 3:
            continue
        if norm in seen:
            continue
        is_dup = False
        for existing in seen:
            shorter = norm if len(norm) <= len(existing) else existing
            longer  = existing if len(norm) <= len(existing) else norm
            if len(shorter) >= 8 and shorter in longer and len(longer) / len(shorter) < 1.6:
                is_dup = True
                break
        if not is_dup:
            seen[norm] = True
            result.append(item)
    return result, len(items) - len(result)


def deduplicate_with_trace(items: list) -> tuple:
    """
    带轨迹的基础去重。
    返回 (去重后列表, 被移除数量, removed_items)。
    removed_items 中保留被判为 exact duplicate 的原始条目及原因。
    """
    seen_norm_titles: dict = {}
    seen_urls: set[str] = set()
    result = []
    removed_items = []
    for item in items:
        norm = normalize_title(item.get('title', ''))
        url = (item.get('url', '') or '').strip()
        if url and url in seen_urls:
            removed_items.append({**item, '_dedup_reason': 'url_exact_match'})
            continue
        if norm and norm in seen_norm_titles:
            removed_items.append({**item, '_dedup_reason': 'normalized_title_exact_match'})
            continue
        if url:
            seen_urls.add(url)
        if norm:
            seen_norm_titles[norm] = True
        result.append(item)
    return result, len(items) - len(result), removed_items


# ── 复盘检测规则 ──────────────────────────────────────
# 宁可漏判，避免把真实催化误标为复盘。
# 单独出现"昨日"不触发（可能是"昨日宣布..."这类新催化）。

RECAP_SIGNALS: list = [
    '复盘',
    '昨日回顾', '本周回顾', '上周回顾', '行情回顾',
    '节前总结', '节后总结', '周度总结', '月度总结', '年度总结', '本月总结',
    '昨天收盘', '昨日收盘',
    '上周表现', '上周行情',
]


def is_recap_item(item: dict) -> bool:
    """判断条目是否为复盘/总结类内容（启发式关键词规则）"""
    text = item.get('title', '') + ' ' + item.get('content', '')
    return any(s in text for s in RECAP_SIGNALS)


# ── 催化类型分类规则 ──────────────────────────────────
# 按优先级排列：earnings > policy > price > overseas > product > capital
# 同一条目只返回第一个命中类型（优先级高的在前）。

CATALYST_PATTERNS: dict = {
    'earnings':  ['财报', '业绩', '一季报', '半年报', '年报', '净利润', '营收', '业绩预告'],
    'policy':    ['政策', '国家队', '国务院', '工信部', '发改委', '会议纪要', '规划', '支持', '利好政策'],
    'price':     ['涨价', '提价', '价格上涨', '价格突破', '现货价', '报价上调'],
    'overseas':  ['美股', '英伟达', '台积电', '纳斯达克', '隔夜', '日经', '港股联动'],
    'product':   ['发布', '量产', '出货', '新品发布', '订单', '中标', '投产'],
    'capital':   ['融资', '增持', '回购', '定增', '北向资金', '主力净流入'],
}


def classify_catalyst(item: dict) -> str | None:
    """
    对条目分类催化类型，按 CATALYST_PATTERNS 顺序首次命中即返回。
    返回 None 表示无明确催化。
    """
    text = item.get('title', '') + ' ' + item.get('content', '')
    for ctype, keywords in CATALYST_PATTERNS.items():
        if any(kw in text for kw in keywords):
            return ctype
    return None
