# 编辑层：个股候选合并
# 将 sector.stock_mentions（analysis 层两路合并结果）升级为 stock_candidate 结构，
# 添加正宗度占位字段供 Claude 在 Step 5 填写。
#
# 两路来源（analysis 层已完成合并）：
#   路径 1：雪球 $name(code)$ 格式，有 code 字段
#   路径 2：stocks_dict.csv 名称词典匹配，有 match_type='name_match'，无 code
#
# 被谁调用：editorial_layer/entry.py


_CATALYST_MAP = {
    'earnings': '财报',
    'policy':   '政策',
    'news':     '消息',
}


def _format_driver(catalyst_types: list) -> str:
    if not catalyst_types:
        return '人气讨论'
    labels = [_CATALYST_MAP.get(t, '消息') for t in catalyst_types]
    return '+'.join(dict.fromkeys(labels))  # 保序去重


def merge_stock_candidates(sector: dict) -> list:
    """
    从 sector.stock_mentions 提取候选个股，添加正宗度占位字段。
    返回 stock_candidates 列表（按提及次数降序，analysis 层已排序）。
    """
    candidates = []
    for sm in sector.get('stock_mentions', []):
        cat_types = sm.get('catalyst_types', [])
        candidates.append({
            'code':                  sm.get('code', ''),
            'name':                  sm.get('name', ''),
            'mention_count':         sm.get('mention_count', 0),
            'heat_sum':              sm.get('heat_sum', 0),
            'sources':               sm.get('sources', []),
            'sample_context':        sm.get('sample_context', ''),
            'match_type':            sm.get('match_type', 'xueqiu'),
            'catalyst_types':        cat_types,
            'driver_display':        _format_driver(cat_types),
            # ── 正宗度占位（Claude 在 Step 5 填写）──────────
            'authenticity':          None,   # '核心股' | '边缘受益' | '蹭概念'
            'authenticity_evidence': None,
            'core_reason':           None,
            'source_summary':        None,
        })
    return candidates
