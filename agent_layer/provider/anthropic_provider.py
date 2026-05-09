# agent_layer/provider/anthropic_provider.py
# Anthropic Claude 实现
# json_mode=True 时通过 system prompt 指令保证 JSON 输出

from .base import BaseProvider

_JSON_INSTRUCTION = '\n\n只返回有效的 JSON，不要输出任何其他内容（无注释、无解释、无 markdown 围栏）。'


class AnthropicProvider(BaseProvider):

    def __init__(self, api_key: str, model: str):
        import anthropic as _sdk
        self._client = _sdk.Anthropic(api_key=api_key)
        self._model  = model

    def chat(self, messages: list, *, json_mode: bool = True, timeout: int = 20) -> str:
        system_parts = [m['content'] for m in messages if m.get('role') == 'system']
        user_msgs    = [m for m in messages if m.get('role') != 'system']

        system = '\n'.join(system_parts)
        if json_mode:
            system = (system + _JSON_INSTRUCTION).strip()

        kwargs = {
            'model':      self._model,
            'max_tokens': 1024,
            'messages':   user_msgs,
        }
        if system:
            kwargs['system'] = system

        resp = self._client.messages.create(**kwargs)
        return resp.content[0].text

    def is_available(self) -> bool:
        return bool(self._client.api_key)
