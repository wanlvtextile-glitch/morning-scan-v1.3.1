# agent_layer/provider/factory.py
# create_provider：根据 AgentConfig 实例化正确的 provider

from .base import BaseProvider


def create_provider(config) -> BaseProvider:
    """
    config: AgentConfig 实例
    返回对应 provider 实例，若 provider_name 不支持则抛 ValueError。
    """
    name = config.provider_name.lower()

    if name == 'anthropic':
        from .anthropic import AnthropicProvider
        return AnthropicProvider(
            api_key=config.anthropic_key,
            model=config.model,
        )

    if name == 'openai':
        from .openai_compat import OpenAIProvider
        return OpenAIProvider(
            api_key=config.openai_key,
            model=config.model,
            base_url=config.openai_base_url,
        )

    raise ValueError(f'未知 LLM_PROVIDER: {name!r}（支持 anthropic / openai）')
