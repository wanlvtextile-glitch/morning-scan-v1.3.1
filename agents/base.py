# agents/base.py
# BaseAgent：agent 公共能力（LLM 调用、JSON 解析、提示词加载）
# 所有 impl/ 下的具体 agent 继承此类

import json
import os
import re
import time


class BaseAgent:

    def __init__(self, provider, config):
        self._provider  = provider
        self._config    = config
        self.call_count = 0
        self.total_ms   = 0

    def _call_llm(self, messages: list, *, json_mode: bool = True, timeout: int = None):
        """调用 LLM，带重试，返回文本或 None（失败时）。"""
        _timeout = timeout or self._config.timeout_seconds
        max_r    = self._config.max_retries

        for attempt in range(max_r + 1):
            try:
                t0   = time.time()
                text = self._provider.chat(messages, json_mode=json_mode, timeout=_timeout)
                self.call_count += 1
                self.total_ms   += int((time.time() - t0) * 1000)
                return text
            except Exception as e:
                if attempt < max_r:
                    time.sleep(1.5 ** attempt)
                    continue
                print(f'[Agent] LLM 调用失败（尝试 {attempt + 1} 次）：{e}')
                return None

    def _parse_json(self, text: str):
        """健壮 JSON 解析：直接解析 → 提取代码块 → 提取首个对象/数组。"""
        if not text:
            return None
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        m = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        m = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        print(f'[Agent] JSON 解析失败，原文前 200 字：{text[:200]}')
        return None

    def _load_prompt(self, filename: str) -> str:
        """从 agents/prompts/ 加载提示词文件。"""
        path = os.path.join(os.path.dirname(__file__), 'prompts', filename)
        with open(path, encoding='utf-8') as f:
            return f.read().strip()
