import importlib
import json
import os
import sys
from typing import List, Set


def load_env(root_dir: str = None) -> bool:
    if root_dir is None:
        root_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(root_dir, '.env')
    if not os.path.exists(env_path):
        return False

    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
    return True


def _load_enabled_source_keys(root_dir: str) -> Set[str]:
    config_path = os.path.join(root_dir, 'config', 'source_registry.json')
    default_keys = {'taoguba', 'ths_news', 'ths_hotrank', 'xueqiu'}
    if not os.path.exists(config_path):
        return default_keys

    try:
        with open(config_path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return default_keys

    enabled = set()
    for item in data.get('sources', []):
        if isinstance(item, dict) and item.get('enabled', True):
            key = str(item.get('key', '')).strip()
            if key:
                enabled.add(key)
    return enabled or default_keys


def _missing_env(names: List[str]) -> List[str]:
    return [name for name in names if not os.environ.get(name, '').strip()]


def check_env() -> dict:
    root = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(root, '.env')
    enabled_sources = _load_enabled_source_keys(root)

    result = {
        'env_file': {'ok': False, 'path': env_path},
        'cookie': {'ok': False, 'hint': ''},
        'agent': {'enabled': False},
        'llm': {'ok': True, 'provider': '', 'hint': ''},
        'errors': [],
        'warnings': [],
        'ready': False,
    }

    if not os.path.exists(env_path):
        result['errors'].append(
            '.env 不存在。\n'
            '  请先复制 .env.example 为 .env，再补齐必填环境变量。'
        )
        return result

    result['env_file']['ok'] = True
    load_env(root)

    if 'xueqiu' in enabled_sources:
        cookie = os.environ.get('XUEQIU_COOKIE', '').strip()
        if cookie:
            result['cookie']['ok'] = True
        else:
            result['errors'].append(
                'XUEQIU_COOKIE 未填写。\n'
                '  当前已启用雪球主源，必须在 .env 中补齐 XUEQIU_COOKIE。'
            )

    if 'zsxq' in enabled_sources:
        required_zsxq = [
            'ZSXQ_AUTHORIZATION',
            'ZSXQ_USER_AGENT',
            'ZSXQ_X_VERSION',
            'ZSXQ_X_SIGNATURE',
            'ZSXQ_X_ADUID',
        ]
        missing = _missing_env(required_zsxq)
        if missing:
            result['errors'].append(
                'ZSXQ 主源环境变量未填写完整。\n'
                f'  缺失：{", ".join(missing)}\n'
                '  当前 morning-scan 已将 ZSXQ 作为主源，未补齐前禁止继续执行。'
            )

    if 'twitter' in enabled_sources:
        if not os.environ.get('APIFY_TOKEN', '').strip():
            result['errors'].append(
                'APIFY_TOKEN 未填写。\n'
                '  当前已启用 Twitter 源，必须在 .env 中补齐 APIFY_TOKEN。'
            )

    agent_enabled = os.environ.get('AGENT_LAYER_ENABLED', 'false').lower() == 'true'
    result['agent']['enabled'] = agent_enabled

    if not agent_enabled:
        result['errors'].append(
            'AGENT_LAYER_ENABLED=false。\n'
            '  你的目标是由 LLM 参与生成最终 morning-scan 报告，'
            '因此 Agent 层必须开启，未开启前不允许继续执行。'
        )
    else:
        provider = os.environ.get('LLM_PROVIDER', '').strip()
        model = os.environ.get('LLM_MODEL', '').strip()
        result['llm']['provider'] = provider

        if not provider:
            result['errors'].append(
                'LLM_PROVIDER 未填写。\n'
                '  请选择 anthropic 或 openai-compatible 服务。'
            )
            result['llm']['ok'] = False
        if not model:
            result['errors'].append(
                'LLM_MODEL 未填写。\n'
                '  开启 Agent 后必须明确指定最终用于出报告的模型。'
            )
            result['llm']['ok'] = False

        if provider == 'anthropic':
            missing = _missing_env(['ANTHROPIC_API_KEY'])
            if missing:
                result['errors'].append(
                    'LLM_PROVIDER=anthropic 但 ANTHROPIC_API_KEY 未填写。'
                )
                result['llm']['ok'] = False
        elif provider == 'openai':
            missing = _missing_env(['OPENAI_API_KEY', 'OPENAI_BASE_URL'])
            if missing:
                result['errors'].append(
                    'LLM_PROVIDER=openai 但 OpenAI-compatible 配置未填写完整。\n'
                    f'  缺失：{", ".join(missing)}'
                )
                result['llm']['ok'] = False
        elif provider:
            result['errors'].append(
                f'LLM_PROVIDER="{provider}" 不受支持，只允许 anthropic 或 openai。'
            )
            result['llm']['ok'] = False

    result['ready'] = len(result['errors']) == 0
    return result


def check_packages() -> dict:
    required = {
        'requests': 'requests',
        'bs4': 'beautifulsoup4',
        'lxml': 'lxml',
        'dateutil': 'python-dateutil',
        'chinese_calendar': 'chinesecalendar',
        'akshare': 'akshare',
    }

    root = os.path.dirname(os.path.abspath(__file__))
    load_env(root)
    provider = os.environ.get('LLM_PROVIDER', '').strip()
    if provider == 'anthropic':
        required['anthropic'] = 'anthropic'
    elif provider == 'openai':
        required['openai'] = 'openai'

    missing = []
    installed = []
    for import_name, pip_name in required.items():
        try:
            importlib.import_module(import_name)
            installed.append(pip_name)
        except ImportError:
            missing.append(pip_name)

    return {
        'ok': len(missing) == 0,
        'missing': missing,
        'installed': installed,
    }


def assert_ready() -> None:
    result = check_env()
    if result['ready']:
        print('[环境检查] OK')
        return

    print('\n[morning-scan 阻断] 环境变量未配置完整，停止执行。\n')
    for i, err in enumerate(result['errors'], 1):
        print(f'  {i}. {err}\n')
    print(f'  配置文件路径：{result["env_file"]["path"]}')
    print('  参考模板：.env.example')
    print('\n  补齐后重新运行：python cli.py run\n')
    sys.exit(1)
