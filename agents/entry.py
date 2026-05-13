import json
import os
import time


def run_agents(state, agent_classes=None) -> None:
    from agents.config import AgentConfig
    from agents.provider.factory import create_provider

    cfg = AgentConfig()
    state.meta['agent_enabled'] = cfg.enabled

    if not cfg.enabled:
        raise RuntimeError('AGENT_LAYER_ENABLED=false，已禁止继续生成最终 morning-scan 报告。')

    provider = create_provider(cfg)
    if not provider.is_available():
        raise RuntimeError('LLM Provider 不可用，已禁止继续生成最终 morning-scan 报告。')

    if agent_classes is None:
        from agents.impl.info_enrichment import InfoEnrichmentAgent
        from agents.impl.semantic_judgment import SemanticJudgmentAgent
        agent_classes = [InfoEnrichmentAgent, SemanticJudgmentAgent]

    t_start = time.time()
    total_calls = 0

    for agent_class in agent_classes:
        agent = agent_class(provider, cfg)
        agent.enrich(state)
        total_calls += agent.call_count
        print(
            f'[Agent] {agent_class.__name__} 完成：'
            f'{agent.call_count} 次调用，{agent.total_ms} ms'
        )

    duration = int(time.time() - t_start)
    state.meta['agent_calls_made'] = total_calls
    state.meta['agent_duration_sec'] = duration
    print(f'[Agent] 合计 {total_calls} 次 LLM 调用，耗时 {duration}s')


def write_scan_result(state, output_dir: str = '.') -> str:
    payload = {
        'meta': state.meta,
        'editorial': state.editorial,
    }
    os.makedirs(output_dir, exist_ok=True)
    scan_date = state.meta.get('scan_date', 'unknown')
    path = os.path.join(output_dir, f'{scan_date}-scan_result.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'[scan_result] 写入 {path}')
    return path
