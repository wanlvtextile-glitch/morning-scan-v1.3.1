# agents/interface.py
# ScanAgentInterface：通用扫描 agent 接口
#
# 任何实现此接口的 agent 均可通过 run_agents(state, agent_classes=[...]) 接入，
# 调用方无需修改——只需传入新的 agent_classes 列表。
#
# 合约：
#   enrich(state) 原地填充 state.editorial 中的 None 占位字段
#   不抛出异常（内部捕获，静默降级）
#   call_count / total_ms 供调用方统计费用与耗时

from abc import ABC, abstractmethod


class ScanAgentInterface(ABC):

    @abstractmethod
    def enrich(self, state) -> None:
        """
        接收 ScanState，原地填充 editorial 字段。
        实现方必须保证：
          1. 不修改 state.analysis / state.preprocess（只读）
          2. 不修改 editorial 中已由 Python 层确定的字段（stage/group/scores）
          3. 捕获所有异常，失败时保持 None 占位不变
        """

    @property
    @abstractmethod
    def call_count(self) -> int:
        """本次 enrich() 消耗的 LLM 调用次数"""

    @property
    @abstractmethod
    def total_ms(self) -> int:
        """本次 enrich() 总耗时（毫秒）"""
