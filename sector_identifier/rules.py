import re


SECTOR_KEYWORDS: dict[str, list[str]] = {
    '半导体': [
        '芯片', '晶圆', '存储', '先进封装', 'EDA', '光刻', 'HBM', 'DRAM', 'NAND',
        '刻蚀', '集成电路', '封装测试', 'AI芯片', '国产芯片', '寒武纪', '中芯',
        '半导体设备', 'IGBT', 'MCU', '功率半导体', '碳化硅', 'SiC', '模拟芯片',
    ],
    'AI算力': [
        'GPU', 'NPU', '服务器', '液冷', 'CPO', '光模块', '算力', '推理', '训练',
        '大模型', '智算', 'AI基础设施', '数据中心',
    ],
    '机器人': [
        '人形机器人', '具身智能', '减速器', '丝杠', '执行器', '机器人', '工业自动化',
        '自动化设备', '六轴', '协作机器人',
    ],
    '新能源': [
        '锂电', '储能', '光伏', '风电', '充电桩', '钠离子', '固态电池',
        '磷酸铁锂', '三元材料', '隔膜', '负极', '正极', '电解液',
        '动力电池', '电池', '新能源车', '储能电站', '光储',
    ],
    '能源金属': [
        '锂矿', '锂价', '碳酸锂', '氧化锂', '钴价', '镍价', '铜矿', '稀土',
        '矿产资源', '能源金属', '有色金属', '锂资源',
    ],
    '创新药': [
        '新药', '临床', '医保', 'ADC', 'GLP-1', '仿制药', 'CXO', 'CDMO',
        '生物医药', '创新药', 'mRNA', '靶向药', 'PD-1', '抗体',
    ],
    '军工': [
        '航空发动机', '无人机', '军工股', '军费', '商业航天', '战机',
        '国防军工', '导弹', '导弹防御', '反无人机',
    ],
    '消费': [
        '白酒', '餐饮', '旅游', '免税', '电商', '零售', '茅台',
        '消费复苏', '出行', '商超', '奶茶',
    ],
    '金融': [
        '券商', '保险', '降准', '流动性宽松', '货币政策', '公募基金',
        '资本市场', '降息', '银行', '非银',
    ],
}

HOTRANK_MAPPING: list[tuple[str, str]] = [
    ('半导体', '半导体'), ('芯片', '半导体'), ('集成电路', '半导体'),
    ('光模块', 'AI算力'), ('算力', 'AI算力'), ('AI', 'AI算力'),
    ('人工智能', 'AI算力'), ('数据中心', 'AI算力'),
    ('人形机器人', '机器人'), ('机器人', '机器人'), ('自动化', '机器人'),
    ('通用设备', '机器人'),
    ('光伏', '新能源'), ('储能', '新能源'), ('锂电池', '新能源'),
    ('风电', '新能源'), ('充电桩', '新能源'), ('新能源', '新能源'),
    ('能源金属', '能源金属'), ('锂矿', '能源金属'), ('稀土', '能源金属'),
    ('有色', '能源金属'), ('金属新材料', '能源金属'),
    ('创新药', '创新药'), ('生物医药', '创新药'), ('医药', '创新药'),
    ('CXO', '创新药'),
    ('军工', '军工'), ('国防', '军工'), ('航天', '军工'),
    ('白酒', '消费'), ('旅游', '消费'), ('零售', '消费'),
    ('消费', '消费'), ('餐饮', '消费'),
    ('银行', '金融'), ('券商', '金融'), ('保险', '金融'),
    ('金融', '金融'),
]

HOTRANK_EXACT_MAPPING: dict[str, str] = {
    '其他电源设备': '新能源',
    '电力': '新能源',
    '电网设备': '新能源',
    '风电设备': '新能源',
    '光伏设备': '新能源',
    '金属新材料': '能源金属',
    '消费电子': '消费',
    '其他电子': '消费',
    '互联网电商': '消费',
    '影视院线': '消费',
    '电子化学品': '半导体',
    '半导体': '半导体',
    '元件': '半导体',
    '通信服务': 'AI算力',
    '通信设备': 'AI算力',
    'IT服务': 'AI算力',
    '软件开发': 'AI算力',
    '自动化设备': '机器人',
    '通用设备': '机器人',
    '军工装备': '军工',
    '军工电子': '军工',
}

MILITARY_FALSE_POSITIVE_SIGNALS: list[str] = [
    '以色列', '以军', '哈马斯', '乌克兰', '俄罗斯', '俄军', '北约',
    '巴勒斯坦', '加沙', '伊朗', '胡塞武装', '黎巴嫩', '真主党',
    '扎波罗热', '国际原子能', '五角大楼', '五角大厦',
]

NOISE_TITLE_KEYWORDS: list[str] = [
    '今日段子', '机构纪要', '更新机构纪要', '复盘', '午评', '收评', '早报',
    '汇总', '标题梳理', '市场情绪', '操作记录',
]

_COMPANY_NAME_RE = re.compile(
    r'[\u4e00-\u9fffA-Za-z]{2,12}(?:股份|科技|电气|电子|精密|材料|通信|能源|智家|集团|电力|光电|新材)'
)


def is_military_false_positive(item: dict) -> bool:
    text = item.get('title', '') + ' ' + item.get('content', '')
    return any(s in text for s in MILITARY_FALSE_POSITIVE_SIGNALS)


def _contains_company_entity(text: str) -> bool:
    return bool(_COMPANY_NAME_RE.search(text or ''))


def _is_noise_item(item: dict) -> bool:
    title = item.get('title', '') or ''
    content = item.get('content', '') or ''
    text = f'{title} {content}'

    if any(keyword in title for keyword in NOISE_TITLE_KEYWORDS):
        return not _contains_company_entity(text)

    if '、' in title or '/' in title:
        if not _contains_company_entity(text):
            return True

    return False


def match_sectors_detail(item: dict) -> dict:
    text = item.get('title', '') + ' ' + item.get('content', '')
    if _is_noise_item(item):
        return {}

    result: dict[str, list[str]] = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        matched_kws = [kw for kw in keywords if kw in text]
        if not matched_kws:
            continue
        if sector == '军工' and is_military_false_positive(item):
            continue
        result[sector] = matched_kws
    return result


def hotrank_name_to_sector(hs_name: str) -> str | None:
    exact_sector = HOTRANK_EXACT_MAPPING.get((hs_name or '').strip())
    if exact_sector:
        return exact_sector
    for kw, sector in HOTRANK_MAPPING:
        if kw in hs_name:
            return sector
    return None


def parse_hotrank(hotrank_items: list) -> tuple[list, dict]:
    hotrank_list = []
    for item in hotrank_items:
        rank = item.get('heat', 999)
        name = item.get('title', '')
        content = item.get('content', '')
        match = re.search(r'涨跌幅[:：]\s*([+\-\d.]+%?)', content)
        change_pct = match.group(1) if match else ''
        hotrank_list.append({'rank': rank, 'name': name, 'change_pct': change_pct})

    hotrank_list.sort(key=lambda x: x['rank'])

    sector_to_hotrank: dict[str, dict] = {}
    for entry in hotrank_list:
        our_sector = hotrank_name_to_sector(entry['name'])
        if our_sector is None:
            continue
        if our_sector not in sector_to_hotrank or entry['rank'] < sector_to_hotrank[our_sector]['rank']:
            sector_to_hotrank[our_sector] = {
                'rank': entry['rank'],
                'name': entry['name'],
                'change_pct': entry['change_pct'],
            }

    return hotrank_list, sector_to_hotrank
