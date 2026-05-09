# 输出层下游消费接口
# 输入：report_result（output_layer/entry.py 的输出对象）
# 返回：各子对象
# 被谁调用：analyzer._analyze()，以及未来外部消费方


def get_report_payload(report_result: dict) -> dict:
    return report_result['report_payload']


def get_markdown(report_result: dict) -> str:
    return report_result['markdown']


def get_groups(report_result: dict) -> dict:
    return report_result['report_payload']['groups']


def get_trigger_summary(report_result: dict) -> list:
    return report_result['report_payload']['trigger_summary']


# ── 新路径访问器（build_report_from_editorial 返回值）────

def get_report_package(report_result: dict) -> dict:
    return report_result['report_package']


def get_brief_markdown(report_result: dict) -> str:
    return report_result['brief_markdown']


def get_sector_intelligence(report_result: dict) -> list:
    return report_result['report_package']['sector_intelligence']


def get_stock_pool(report_result: dict) -> list:
    return report_result['report_package']['stock_pool']
