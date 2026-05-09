# 早盘热点扫描 v1.3

每日开盘前自动采集四路数据源，识别市场热点板块和个股，由 LLM Agent 补全正宗度判断和结论，输出结构化早盘报告。

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 XUEQIU_COOKIE 和 LLM API Key

# 3. 运行
python run.py "启动早盘扫描"
```

---

## 系统架构

```
python run.py "启动早盘扫描"
        │
  [pipeline.py]          全流程串联
        │
  [collector/]           采集层：四源并行（淘股吧/同花顺早报/人气榜/雪球）
        │                         + akshare 自动拉取 A股指数/美股数据
        ↓ raw_news.json
  [analyzer.py]          分析编排
    ├── preprocessor/    去重 / recap / catalyst 分类
    ├── sector_identifier/  9板块聚类（cross-sector 权重）
    ├── analysis/        热度评分 / 阶段判断 / 个股提取
    ├── dual_score/      续强评分 / 发酵评分 / 盘中验证点
    ├── editorial_layer/ 整合编辑结构
    ├── agent_layer/     LLM 补全：正宗度 / 关注标的 / 综合结论
    └── output_layer/    生成 Markdown 报告草稿
        │
  四路输出：
    ├── analysis_result.json             中间产物
    ├── YYYY-MM-DD-scan_result.json      最终结构化产物（含 agent 补全）
    ├── reports/YYYY-MM-DD-morning-scan.md       主报告
    └── reports/YYYY-MM-DD-morning-scan-brief.md 简报
```

---

## 安装步骤

### 1. 依赖安装

```bash
pip install -r requirements.txt
```

主要依赖：`requests` / `beautifulsoup4` / `akshare` / `chinesecalendar` / `anthropic` / `openai`

### 2. 雪球 Cookie 配置（必填）

雪球数据源需要登录态 Cookie，获取方式：

1. 浏览器登录 [xueqiu.com](https://xueqiu.com)
2. 打开开发者工具（F12）→ Network 标签
3. 随意点击页面触发任意请求，找到 `xueqiu.com` 域名的请求
4. 在 Request Headers 中找到 `Cookie` 字段，复制完整值
5. 粘贴到 `.env` 的 `XUEQIU_COOKIE=` 后

> Cookie 有效期约 30 天，过期后重新提取。过期特征：运行时出现 `cookie_expired` 错误。

### 3. LLM API 配置

Agent 层支持多种服务商，选择一种填入 `.env` 即可，无需修改代码。

**选项 1：DeepSeek**

注册 [platform.deepseek.com](https://platform.deepseek.com) 获取 API Key，充值约 ¥10 可跑数百次。

```env
AGENT_LAYER_ENABLED=true
LLM_PROVIDER=openai
LLM_MODEL=deepseek-chat
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

**选项 2：智谱 AI / GLM**

注册 [open.bigmodel.cn](https://open.bigmodel.cn) 获取 API Key，`glm-4-flash` 有免费额度。

```env
AGENT_LAYER_ENABLED=true
LLM_PROVIDER=openai
LLM_MODEL=glm-4-flash
OPENAI_API_KEY=xxx.xxx
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

**选项 3：Anthropic Claude**

从 [console.anthropic.com](https://console.anthropic.com) 获取 API Key（格式 `sk-ant-api03-...`）。

```env
AGENT_LAYER_ENABLED=true
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-api03-xxx
```

**选项 4：其他 OpenAI-compatible 服务商**

小米、MiniMax、月之暗面（Kimi）、硅基流动等均支持，填入服务商提供的 Base URL 和模型名即可。

```env
AGENT_LAYER_ENABLED=true
LLM_PROVIDER=openai
LLM_MODEL=<服务商模型名>
OPENAI_API_KEY=<服务商 API Key>
OPENAI_BASE_URL=<服务商 Base URL>
```

**关闭 Agent 层（仅 Python 分析，无 LLM）：**

```env
AGENT_LAYER_ENABLED=false
```

---

## 配置文件说明

### `.env`

| 变量 | 必填 | 说明 |
|------|------|------|
| `XUEQIU_COOKIE` | ✅ | 雪球登录 Cookie |
| `AGENT_LAYER_ENABLED` | ✅ | `true` 启用 LLM 补全，`false` 仅 Python |
| `LLM_PROVIDER` | agent启用时必填 | `openai`（DeepSeek / 智谱 / 小米等兼容服务商）或 `anthropic` |
| `LLM_MODEL` | agent启用时必填 | 服务商模型名，如 `deepseek-chat` / `glm-4-flash` 等 |
| `ANTHROPIC_API_KEY` | 选项3必填 | Anthropic API Key（格式 `sk-ant-api03-...`） |
| `OPENAI_API_KEY` | 选项1/2/4必填 | 对应服务商的 API Key |
| `OPENAI_BASE_URL` | 选项1/2/4必填 | 服务商 API Base URL |

### `config/agent_config.json`

控制 Agent 节点的开关和费用上限，默认配置已可直接使用：

```json
{
  "max_llm_calls_per_run": 40,   // 单次运行最大 LLM 调用次数，超出警告
  "agents": {
    "info_enrichment": { "enabled": true },   // hotrank摘要 + 关注个股
    "semantic_judgment": { "enabled": true }  // 正宗度 + 板块审核 + 结论
  }
}
```

### `stocks_dict.csv`

全量 A 股名称词典（5246条），用于个股提取的名称匹配。**必须保留在项目根目录**，不可删除。

---

## 输出文件说明

| 文件 | 说明 |
|------|------|
| `raw_news.json` | 采集层原始输出，每次运行覆盖 |
| `analysis_result.json` | Python 分析层中间产物，不含 agent 数据 |
| `YYYY-MM-DD-scan_result.json` | 含 agent 补全的最终结构化产物 |
| `reports/YYYY-MM-DD-morning-scan.md` | 当日主报告 |
| `reports/YYYY-MM-DD-morning-scan-brief.md` | 当日简报 |

---

## 完整性验证

安装完成后，运行以下命令验证各模块可正常导入：

```bash
# 验证核心模块
python -c "from collector.entry import collect; print('collector OK')"
python -c "from agents import assemble_state, run_agents, write_scan_result; print('agents OK')"

# 运行测试（需安装 pytest）
pip install pytest
python -m pytest tests/ -q
# 预期：约 298 passed，已知失败 6 个（3个 compute_stage + 2个美股网络 + 1个集成测试）
```

---

## 数据来源与依赖

| 来源 | 类型 | 说明 |
|------|------|------|
| 淘股吧 | 论坛热帖 | JSON API，无需认证 |
| 同花顺早报 | 官方资讯 | JS 文件，无需认证 |
| 同花顺人气榜 | 人气排行 | HTML，无需认证 |
| 雪球 | 投资社区 | JSON API，需 Cookie |
| akshare | A股/美股指数 | 开源库，自动拉取 |

---

## 常见问题

**Q：雪球数据获取失败**  
A：检查 `.env` 中 `XUEQIU_COOKIE` 是否有效，Cookie 约 30 天过期需重新提取。

**Q：Agent 层调用失败**  
A：检查 API Key 余额和网络连通性。Agent 层失败会静默降级，报告仍可正常生成。

**Q：美股数据拉取失败（ProxyError）**  
A：akshare 的美股接口依赖网络环境，代理环境下可能失败，不影响主流程。

**Q：`stocks_dict.csv` 找不到**  
A：确认该文件在项目根目录（与 `run.py` 同级）。

---

## 版本

- v1.3.1（2026-05-09）：个股跨板块污染修复（`_weight >= 0.5` 过滤）
- v1.3.0（2026-05-08）：Agent 层全量实现（DeepSeek / 智谱 / Anthropic / 任意 OpenAI-compatible 服务商）
- v1.2.x（2026-05-05~07）：采集层并行化 / 编辑层 / 双评分层 / 个股信息增强
