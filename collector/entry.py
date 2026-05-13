# 采集入口（对外接口）
# 供任务触发层（run.py）调用的唯一对外函数：collect()
# 职责：加载环境变量，然后委托编排层执行采集。
# collector 包内其他模块不直接对外暴露。

import os


def _load_env():
    """从项目根目录的 .env 文件加载环境变量（不覆盖已有的系统变量）"""
    # __file__ 是 collector/entry.py，向上一级是项目根目录
    env_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..', '.env')
    )
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


def collect(websearch_data: list = None):
    """
    执行早盘采集，返回 CollectorOutput。
    websearch_data 可选，由 Claude 执行 WebSearch 后传入，作为补充源注入输出。
    文件写入由调用方（pipeline.py）负责。
    """
    _load_env()

    # 延迟导入：确保 .env 已加载后再触发模块级的环境变量读取（如 XUEQIU_COOKIE）
    from collector.orchestrator import run_collection
    return run_collection(websearch_data=websearch_data)
