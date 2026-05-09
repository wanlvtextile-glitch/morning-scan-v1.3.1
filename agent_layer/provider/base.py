# agent_layer/provider/base.py
# BaseProvider：LLM 调用抽象接口
# 所有 provider 实现必须继承此类

from abc import ABC, abstractmethod


class BaseProvider(ABC):

    @abstractmethod
    def chat(
        self,
        messages: list,
        *,
        json_mode: bool = True,
        timeout: int = 20,
    ) -> str:
        """
        发送 messages 并返回模型回复文本。
        messages 格式：[{"role": "system"|"user"|"assistant", "content": str}]
        json_mode=True 时 provider 层负责确保响应为合法 JSON。
        """
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """检查 provider 是否可用（API Key 已配置且非空）。"""
        raise NotImplementedError
