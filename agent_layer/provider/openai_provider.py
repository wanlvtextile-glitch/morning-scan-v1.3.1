# agent_layer/provider/openai_provider.py
# OpenAI-compatible 实现（GPT / DeepSeek / Qwen / Ollama 均可）
# 通过 OPENAI_BASE_URL 切换后端

from .base import BaseProvider

_JSON_INSTRUCTION = '\n\n只返回有效的 JSON，不要输出任何其他内容（无注释、无解释、无 markdown 围栏）。'


class OpenAIProvider(BaseProvider):

    def __init__(self, api_key: str, model: str, base_url: str = ''):
        from openai import OpenAI as _SDK
        kwargs = {'api_key': api_key}
        if base_url:
            kwargs['base_url'] = base_url
        self._client  = _SDK(**kwargs)
        self._model   = model
        self._api_key = api_key

    def chat(self, messages: list, *, json_mode: bool = True, timeout: int = 20) -> str:
        if json_mode:
            msgs = list(messages)
            sys_idx = next((i for i, m in enumerate(msgs) if m.get('role') == 'system'), None)
            if sys_idx is not None:
                msgs[sys_idx] = {
                    **msgs[sys_idx],
                    'content': msgs[sys_idx]['content'] + _JSON_INSTRUCTION,
                }
            else:
                msgs.insert(0, {'role': 'system', 'content': _JSON_INSTRUCTION.strip()})
            extra = {'response_format': {'type': 'json_object'}}
        else:
            msgs  = messages
            extra = {}

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=msgs,
            timeout=timeout,
            **extra,
        )
        return resp.choices[0].message.content

    def is_available(self) -> bool:
        return bool(self._api_key)
