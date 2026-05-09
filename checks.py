# checks.py — 共享环境校验层
#
# 供 pipeline.py（启动门禁）和 cli.py（诊断展示）共同调用。
# 不依赖任何第三方库，只用标准库。

import importlib
import os
import sys

# ── .env 加载 ─────────────────────────────────────────────

def load_env(root_dir: str = None) -> bool:
    """
    从项目根目录加载 .env（不覆盖已有系统变量）。
    返回 True 表示文件存在并已加载，False 表示文件不存在。
    """
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


# ── 环境校验 ──────────────────────────────────────────────

def check_env() -> dict:
    """
    校验运行所需的全部环境配置，返回结构化结果。
    调用前会自动加载 .env。

    返回格式：
    {
        'env_file':    {'ok': bool, 'path': str},
        'cookie':      {'ok': bool, 'hint': str},
        'agent':       {'enabled': bool},
        'llm':         {'ok': bool, 'provider': str, 'hint': str},
        'errors':      [str, ...],   # 阻断性错误
        'warnings':    [str, ...],   # 非阻断性提示
        'ready':       bool,         # False 表示无法运行
    }
    """
    root = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(root, '.env')

    result = {
        'env_file':  {'ok': False, 'path': env_path},
        'cookie':    {'ok': False, 'hint': ''},
        'agent':     {'enabled': False},
        'llm':       {'ok': True, 'provider': '', 'hint': ''},
        'errors':    [],
        'warnings':  [],
        'ready':     False,
    }

    # ① .env 文件
    if not os.path.exists(env_path):
        result['errors'].append(
            '.env 配置文件不存在\n'
            '  修复：cp .env.example .env  （然后填写必要项）'
        )
        return result
    result['env_file']['ok'] = True
    load_env(root)

    # ② 雪球 Cookie
    cookie = os.environ.get('XUEQIU_COOKIE', '').strip()
    if cookie:
        result['cookie']['ok'] = True
    else:
        result['errors'].append(
            'XUEQIU_COOKIE 未填写\n'
            '  获取：浏览器登录 xueqiu.com → F12 → Network\n'
            '        → 任意 xueqiu.com 请求 → Request Headers → 复制 Cookie\n'
            '  填写：.env 文件第一行  XUEQIU_COOKIE=<粘贴>'
        )

    # ③ Agent 层 LLM 配置
    agent_enabled = os.environ.get('AGENT_LAYER_ENABLED', 'false').lower() == 'true'
    result['agent']['enabled'] = agent_enabled

    if agent_enabled:
        provider = os.environ.get('LLM_PROVIDER', '').strip()
        result['llm']['provider'] = provider

        if not provider:
            result['errors'].append(
                'AGENT_LAYER_ENABLED=true 但 LLM_PROVIDER 未填写\n'
                '  修复：在 .env 中取消一个服务商方案的注释，并填入 API Key\n'
                '  或者：将 AGENT_LAYER_ENABLED 改为 false（不使用 LLM 分析）'
            )
            result['llm']['ok'] = False
        elif provider == 'anthropic':
            key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
            if not key:
                result['errors'].append(
                    'LLM_PROVIDER=anthropic 但 ANTHROPIC_API_KEY 未填写\n'
                    '  获取：console.anthropic.com → API Keys（格式 sk-ant-api03-...）\n'
                    '  或者：将 AGENT_LAYER_ENABLED 改为 false'
                )
                result['llm']['ok'] = False
        elif provider == 'openai':
            key      = os.environ.get('OPENAI_API_KEY', '').strip()
            base_url = os.environ.get('OPENAI_BASE_URL', '').strip()
            missing  = []
            if not key:
                missing.append('OPENAI_API_KEY')
            if not base_url:
                missing.append('OPENAI_BASE_URL')
            if missing:
                result['errors'].append(
                    f'LLM_PROVIDER=openai 但 {" 和 ".join(missing)} 未填写\n'
                    '  示例：OPENAI_BASE_URL=https://api.deepseek.com/v1\n'
                    '  或者：将 AGENT_LAYER_ENABLED 改为 false'
                )
                result['llm']['ok'] = False
        else:
            result['errors'].append(
                f'LLM_PROVIDER="{provider}" 不支持，仅支持 anthropic 或 openai'
            )
            result['llm']['ok'] = False
    else:
        result['errors'].append(
            'AGENT_LAYER_ENABLED=false：LLM API 未配置，无法生成完整报告\n'
            '  修复：在 .env 中选择一个 LLM 服务商，填入 API Key，\n'
            '        并将 AGENT_LAYER_ENABLED 改为 true\n'
            '  参考：README.md → LLM API 配置章节，或运行 python cli.py run 进入配置向导'
        )

    result['ready'] = len(result['errors']) == 0
    return result


def check_packages() -> dict:
    """
    检查必要 Python 包是否已安装。
    返回 {'ok': bool, 'missing': [str], 'installed': [str]}
    """
    required = {
        'requests':          'requests',
        'bs4':               'beautifulsoup4',
        'lxml':              'lxml',
        'dateutil':          'python-dateutil',
        'chinese_calendar':  'chinesecalendar',
        'akshare':           'akshare',
        'anthropic':         'anthropic',
        'openai':            'openai',
    }
    missing   = []
    installed = []
    for import_name, pip_name in required.items():
        try:
            importlib.import_module(import_name)
            installed.append(pip_name)
        except ImportError:
            missing.append(pip_name)
    return {
        'ok':        len(missing) == 0,
        'missing':   missing,
        'installed': installed,
    }


# ── 门禁函数（供 pipeline 调用）─────────────────────────

def assert_ready() -> None:
    """
    校验环境，若不满足则打印结构化错误提示并 sys.exit(1)。
    供 pipeline.run_pipeline() 在执行前调用（兜底安全门禁）。
    主要错误提示由 cli.cmd_run() 负责；此处作为二次保障。
    """
    result = check_env()
    if result['ready']:
        print('[配置检查] OK')
        return
    print('\n[启动失败] 请先完成以下配置，再重新运行：\n')
    for i, err in enumerate(result['errors'], 1):
        print(f'  {i}. {err}\n')
    print(f'  配置文件路径：{result["env_file"]["path"]}')
    print(f'  配置模板参考：.env.example')
    print(f'\n  配置完成后运行：python cli.py run\n')
    sys.exit(1)
