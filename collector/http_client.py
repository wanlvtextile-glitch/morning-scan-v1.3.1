# 请求与重试层
# 封装带超时控制和自动重试的 HTTP GET 请求。
#
# 超时分三层（职责各不同）：
#   REQUEST_TIMEOUT  - 单次 socket 超时，唯一能中断阻塞请求的机制
#   SOURCE_BUDGET    - 单来源最长允许时间，检查点（请求返回后才生效）
#   GLOBAL_BUDGET    - 全流程最长时间，检查点（由编排层的定时器触发）

import time
import requests
from typing import Optional

# 单次请求超时（秒）
REQUEST_TIMEOUT = 12

# 单来源预算（秒）：超过后停止翻页 / 重试
SOURCE_BUDGET = 25

# 全流程预算（秒）：超过后跳过剩余来源
GLOBAL_BUDGET = 90

# 通用请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 可重试的 HTTP 状态码（服务端临时故障）
RETRYABLE_STATUS = {500, 502, 503, 504}


def is_retryable_error(exc: Exception) -> bool:
    """判断异常是否可以重试（网络超时、连接重置、服务端 5xx）"""
    if isinstance(exc, (requests.exceptions.Timeout,
                        requests.exceptions.ConnectionError,
                        requests.exceptions.ChunkedEncodingError)):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        code = exc.response.status_code if exc.response is not None else 0
        return code in RETRYABLE_STATUS
    return False


def fetch_with_retry(url: str, params: dict = None,
                     headers: dict = None) -> Optional[requests.Response]:
    """
    带一次重试的 GET 请求。
    首次失败且错误可重试时，等待 3 秒后重试一次。
    两次均失败则返回 None。
    """
    _headers = headers if headers is not None else HEADERS
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=_headers, params=params,
                                timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            if attempt == 0 and is_retryable_error(exc):
                time.sleep(3)
                continue
            return None
    return None
