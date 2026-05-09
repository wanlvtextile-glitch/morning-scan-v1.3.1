# 判断规则层
# 负责：板块关键词词典、军工假阳性词典、人气榜映射表，及纯函数实现
# 被谁调用：sector_identifier/conclusions.py、sector_identifier/entry.py

import re


SECTOR_KEYWORDS: dict = {
    '半导体':  ['芯片', '晶圆', '存储', '先进封装', 'EDA', '光刻', 'HBM', 'DRAM', 'NAND',
               '刻蚀', '集成电路', '封装测试', 'AI芯片', '国产芯片', '寒武纪', '中芯'],
    'AI算力':  ['GPU', 'NPU', '服务器', '液冷', 'CPO', '光模块', '算力', '推理', '训练',
               '大模型', '智算', 'AI基础设施', '数据中心'],
    '机器人':  ['人形机器人', '具身智能', '减速器', '丝杠', '执行器', '机器人', '工业自动化',
               '自动化设备', '六轴', '协作机器人'],
    '新能源':  ['锂电', '储能', '光伏', '风电', '充电桩', '钙钛矿', '固态电池',
               '磷酸铁锂', '三元材料', '隔膜', '负极', '正极', '电解液'],
    '能源金属': ['锂矿', '锂价', '碳酸锂', '氢氧化锂', '钴价', '镍价', '铜矿', '稀土',
               '矿产资源', '能源金属', '有色金属', '锂资源'],
    '创新药':  ['新药', '临床', '医保', 'ADC', 'GLP-1', '仿制药', 'CXO', 'CDMO',
               '生物医药', '创新药', 'mRNA', '靶向药', 'PD-1', '抗体'],
    '军工':    ['航空发动机', '无人机袭击', '军工股', '军费', '商业航天', '战机',
               '国防军工', '歼-', '导弹防御', '反无人机'],
    '消费':    ['白酒', '餐饮', '旅游', '免税', '电商', '零售', '茅台',
               '消费复苏', '出行', '商超', '奢侈品'],
    '金融':    ['券商', '保险', '降准', '流动性宽松', '货币政策', '公募基金',
               '资本市场', '降息'],
}

HOTRANK_MAPPING: list = [
    ('半导体',   '半导体'), ('芯片',     '半导体'), ('集成电路', '半导体'),
    ('光模块',   'AI算力'), ('算力',     'AI算力'), ('AI',       'AI算力'),
    ('人工智能', 'AI算力'), ('数据中心', 'AI算力'),
    ('人形机器人', '机器人'), ('机器人',   '机器人'), ('自动化',   '机器人'),
    ('通用设备', '机器人'),
    ('光伏',     '新能源'), ('储能',     '新能源'), ('锂电池',   '新能源'),
    ('风电',     '新能源'), ('充电桩',   '新能源'), ('新能源',   '新能源'),
    ('能源金属', '能源金属'), ('锂矿',     '能源金属'), ('稀土',     '能源金属'),
    ('有色',     '能源金属'), ('金属新材料', '能源金属'),
    ('创新药',   '创新药'), ('生物医药', '创新药'), ('医药',     '创新药'),
    ('CXO',      '创新药'),
    ('军工',     '军工'), ('国防',     '军工'), ('航天',     '军工'),
    ('白酒',     '消费'), ('旅游',     '消费'), ('零售',     '消费'),
    ('消费',     '消费'), ('餐饮',     '消费'),
    ('银行',     '金融'), ('券商',     '金融'), ('保险',     '金融'),
    ('金融',     '金融'),
]

MILITARY_FALSE_POSITIVE_SIGNALS: list = [
    '以色列', '以军', '哈马斯', '乌克兰', '俄罗斯', '俄军', '北约',
    '巴勒斯坦', '加沙', '伊朗', '胡塞武装', '黎巴嫩', '真主党',
    '扎波罗热', '国际原子能', '五角大楼', '五角大厦',
]


def is_military_false_positive(item: dict) -> bool:
    text = item.get('title', '') + ' ' + item.get('content', '')
    return any(s in text for s in MILITARY_FALSE_POSITIVE_SIGNALS)


def match_sectors_detail(item: dict) -> dict:
    """返回 {板块名: [命中关键词]}，军工假阳性在此过滤。"""
    text = item.get('title', '') + ' ' + item.get('content', '')
    result: dict = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        matched_kws = [kw for kw in keywords if kw in text]
        if not matched_kws:
            continue
        if sector == '军工' and is_military_false_positive(item):
            continue
        result[sector] = matched_kws
    return result


def hotrank_name_to_sector(hs_name: str) -> str | None:
    for kw, sector in HOTRANK_MAPPING:
        if kw in hs_name:
            return sector
    return None


def parse_hotrank(hotrank_items: list) -> tuple:
    """
    返回 (hotrank_list, sector_to_hotrank)。
    hotrank_list: [{rank, name, change_pct}] 按排名升序。
    sector_to_hotrank: {板块名 -> {rank, name, change_pct}}。
    """
    hotrank_list = []
    for item in hotrank_items:
        rank    = item.get('heat', 999)
        name    = item.get('title', '')
        content = item.get('content', '')
        import re as _re
        m = _re.search(r'涨跌幅[：:]\s*([+\-\d.]+%?)', content)
        change_pct = m.group(1) if m else ''
        hotrank_list.append({'rank': rank, 'name': name, 'change_pct': change_pct})

    hotrank_list.sort(key=lambda x: x['rank'])

    sector_to_hotrank: dict = {}
    for entry in hotrank_list:
        our_sector = hotrank_name_to_sector(entry['name'])
        if our_sector is None:
            continue
        if (our_sector not in sector_to_hotrank
                or entry['rank'] < sector_to_hotrank[our_sector]['rank']):
            sector_to_hotrank[our_sector] = {
                'rank':       entry['rank'],
                'name':       entry['name'],
                'change_pct': entry['change_pct'],
            }

    return hotrank_list, sector_to_hotrank
