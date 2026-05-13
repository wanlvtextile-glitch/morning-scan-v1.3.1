from __future__ import annotations


def inject_logic_explanations(markdown: str, report_package: dict) -> str:
    sectors = report_package.get('sector_intelligence', []) or []
    updated = markdown

    for sector in sectors:
        name = sector.get('name', '')
        logic_lines = sector.get('logic_summary_lines', []) or []
        if not name or not logic_lines:
            continue

        heading = f'### {name}'
        insert = '\n'.join([heading] + [f'- **逻辑解释**：{logic_lines[0]}'] + [f'- {line}' for line in logic_lines[1:3]])
        updated = updated.replace(heading, insert, 1)

    return updated


def inject_brief_logic_summary(markdown: str, report_package: dict) -> str:
    top_sectors = report_package.get('report_views', {}).get('top_sectors', []) or []
    if not top_sectors:
        return markdown

    lines = ['## 重点逻辑摘要', '']
    for idx, sector in enumerate(top_sectors[:3], 1):
        name = sector.get('name', '')
        short = sector.get('logic_summary_short', '')
        if not name or not short:
            continue
        lines.append(f'{idx}. {name}：{short}')

    if len(lines) <= 2:
        return markdown
    return markdown + '\n\n' + '\n'.join(lines)
