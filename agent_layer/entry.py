# agent_layer/entry.py
# run_agents：Agent 层主编排入口
# write_scan_result：写入唯一最终结构化产物 scan_result.json
# 被谁调用：analyzer._analyze()

import json
import os
import time


def run_agents(state) -> None:
    """
    运行 InfoEnrichmentAgent → SemanticJudgmentAgent，原地填充 state.editorial。
    state.meta 的 agent_enabled / agent_calls_made / agent_duration_sec 由此函数写入。
    若 agent 层未启用或 API Key 缺失，静默跳过，state 保持 None 占位不变。
    """
    from agent_layer.config import AgentConfig
    from agent_layer.provider.factory import create_provider
    from agent_layer.agents.info_enrichment import InfoEnrichmentAgent
    from agent_layer.agents.semantic_judgment import SemanticJudgmentAgent

    cfg = AgentConfig()
    state.meta['agent_enabled'] = cfg.enabled

    if not cfg.enabled:
        print('[Agent] AGENT_LAYER_ENABLED=false，跳过 agent 层')
        return

    provider = create_provider(cfg)
    if not provider.is_available():
        print('[Agent] Provider API Key 未配置，跳过 agent 层')
        state.meta['agent_enabled'] = False
        return

    t_start     = time.time()
    total_calls = 0

    try:
        info_agent = InfoEnrichmentAgent(provider, cfg)
        info_agent.run(state)
        total_calls += info_agent.call_count
        print(f'[Agent] InfoEnrichment 完成：{info_agent.call_count} 次调用，'
              f'{info_agent.total_ms} ms')

        sem_agent = SemanticJudgmentAgent(provider, cfg)
        sem_agent.run(state)
        total_calls += sem_agent.call_count
        print(f'[Agent] SemanticJudgment 完成：{sem_agent.call_count} 次调用，'
              f'{sem_agent.total_ms} ms')

    except Exception as e:
        print(f'[Agent] 运行异常（降级继续，不影响报告输出）：{e}')

    duration = int(time.time() - t_start)
    state.meta['agent_calls_made']   = total_calls
    state.meta['agent_duration_sec'] = duration
    print(f'[Agent] 合计 {total_calls} 次 LLM 调用，耗时 {duration}s')


def write_scan_result(state, output_dir: str = '.') -> str:
    """
    将 meta + editorial 写入 YYYY-MM-DD-scan_result.json（唯一最终结构化产物）。
    在 run_agents() 之后、build_report_from_editorial() 之前调用。
    返回写入的文件路径。
    """
    payload = {
        'meta':      state.meta,
        'editorial': state.editorial,
    }
    os.makedirs(output_dir, exist_ok=True)
    scan_date = state.meta.get('scan_date', 'unknown')
    path = os.path.join(output_dir, f'{scan_date}-scan_result.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'[scan_result] 写入 {path}')
    return path
