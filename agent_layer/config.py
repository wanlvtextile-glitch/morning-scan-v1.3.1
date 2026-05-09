# agent_layer/config.py
# AgentConfig：从 .env + config/agent_config.json 加载 agent 层配置
# 被谁调用：agent_layer/entry.py, agent_layer/provider/factory.py

import json
import os


def _load_env_file():
    """加载项目根目录 .env（不覆盖已有系统变量）"""
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


class AgentConfig:
    """Agent 层运行时配置。"""

    def __init__(self):
        _load_env_file()

        self.enabled         = os.environ.get('AGENT_LAYER_ENABLED', 'false').lower() == 'true'
        self.provider_name   = os.environ.get('LLM_PROVIDER', 'anthropic')
        self.model           = os.environ.get('LLM_MODEL', 'claude-haiku-4-5-20251001')
        self.anthropic_key   = os.environ.get('ANTHROPIC_API_KEY', '')
        self.openai_key      = os.environ.get('OPENAI_API_KEY', '')
        self.openai_base_url = os.environ.get('OPENAI_BASE_URL', '')

        cfg_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', 'config', 'agent_config.json')
        )
        with open(cfg_path, encoding='utf-8') as f:
            _json = json.load(f)

        self.timeout_seconds = _json.get('timeout_seconds', 25)
        self.max_retries     = _json.get('max_retries', 2)
        self.agents          = _json.get('agents', {})
        self.cost_control    = _json.get('cost_control', {})

    def node_enabled(self, agent_name: str, node_name: str) -> bool:
        agent = self.agents.get(agent_name, {})
        if not agent.get('enabled', True):
            return False
        node = agent.get('nodes', {}).get(node_name, {})
        return node.get('enabled', True)

    def node_cfg(self, agent_name: str, node_name: str) -> dict:
        return self.agents.get(agent_name, {}).get('nodes', {}).get(node_name, {})
