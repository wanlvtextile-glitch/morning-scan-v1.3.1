# 证据留存层
# 存储命中关键词、板块映射等可审计字段
# 被谁调用：sector_identifier/entry.py


def preserve_sector_evidence(item: dict, sector_detail: dict) -> dict:
    """在 item 上追加板块命中证据字段，返回浅拷贝。"""
    return {
        **item,
        '_sector_detail':   sector_detail,
        '_sector_names':    list(sector_detail.keys()),
        '_sector_count':    len(sector_detail),
    }
