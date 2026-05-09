# 双评分层编排入口
# 输入：sectors list（来自 analysis_result['sectors']，不是原始 items）
# 输出：dual_score_result dict（含 scored_sectors + scoring_stats）
# 被谁调用：analyzer._analyze()，在 run_analysis_pipeline 之后、写文件之前

# ── 关于并行执行 ──────────────────────────────────────
# continuation 和 fermentation 两个分支逻辑完全独立，互不依赖。
# v1.2 串行实现，保持最小依赖。
# v1.3 若需加速，可替换为下方的可选并行方案（已附注释）。

from dual_score.continuation import score_continuation
from dual_score.fermentation import score_fermentation
from dual_score.output import build_dual_score_output


def score_sectors(sectors: list) -> dict:
    """
    对 analysis_result['sectors'] 中的每个板块对象执行双评分，
    返回 dual_score_result（scored_sectors 包含原字段 + 新增双评分字段）。

    双评分字段（新增）：
      continuation_score    '高'|'中'|'低'   持续性评分
      continuation_reasons  list[str]        持续性支撑依据
      continuation_risks    list[str]        持续性风险提示
      fermentation_score    '高'|'中'|'低'   次日发酵概率
      fermentation_reasons  list[str]        发酵支撑依据
      trigger_points        list[str]        盘中验证点
    """
    scored = []
    for sector in sectors:
        cont = score_continuation(sector)
        ferm = score_fermentation(sector)
        # 原始字段全保留，追加双评分字段
        scored.append({**sector, **cont, **ferm})

    return build_dual_score_output(scored)


# ── 可选并行方案（v1.3 参考，当前未启用）────────────────
# from concurrent.futures import ThreadPoolExecutor
#
# def _score_one(sector: dict) -> dict:
#     cont = score_continuation(sector)
#     ferm = score_fermentation(sector)
#     return {**sector, **cont, **ferm}
#
# def score_sectors_parallel(sectors: list) -> dict:
#     with ThreadPoolExecutor(max_workers=4) as pool:
#         scored = list(pool.map(_score_one, sectors))
#     return build_dual_score_output(scored)
