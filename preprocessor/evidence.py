# 证据留存层
# 输入：单条 item dict（已含结论字段）
# 输出：含证据字段的 item dict（浅拷贝）
# 被谁调用：preprocessor/entry.py

EVIDENCE_FIELDS: list = ['title', 'content', 'source', 'url', 'published_at', 'heat']

EVIDENCE_DEFAULTS: dict = {
    'title':        '',
    'content':      '',
    'source':       '',
    'url':          '',
    'published_at': '',
    'heat':         0,
}


def preserve_evidence(item: dict) -> dict:
    """保留证据字段，补全缺失键为默认值，返回浅拷贝。"""
    result = {**item}
    for field, default in EVIDENCE_DEFAULTS.items():
        if field not in result:
            result[field] = default
    return result
