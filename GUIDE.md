# 使用说明 — 早盘热点扫描

---

## 这个 skill 是什么

早盘热点扫描是一个运行在 Claude Code 中的自动化工具。每个交易日开盘前，你说一句触发词，它会自动完成以下工作：

1. 从淘股吧、同花顺、雪球同时采集隔夜资讯
2. 识别当日热点板块（半导体、AI算力、机器人、新能源等 9 个方向）
3. 评估每个板块的热度、发展阶段、持续性
4. 筛选核心个股，判断正宗度（核心股 / 边缘受益 / 蹭概念）
5. 输出结构化早盘报告到 `reports/` 目录

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.8 及以上 |
| Claude Code | 已安装并登录 |
| 网络 | 可访问淘股吧、同花顺、雪球 |
| LLM API | 任选一个服务商（见下方配置项） |

---

## 安装步骤

**第一步：安装 Python 依赖**

```bash
pip install -r requirements.txt
```

**第二步：创建配置文件**

```bash
cp .env.example .env
```

用文本编辑器打开 `.env`，填写必要配置（见下方）。

**第三步：验证安装**

```bash
python -c "from collector.entry import collect; print('OK')"
python -c "from agents import run_agents; print('OK')"
```

两行均输出 `OK` 即安装成功。

---

## 必填配置项

打开 `.env` 文件，填写以下内容：

### 1. 雪球 Cookie（必填）

```
XUEQIU_COOKIE=<你的 Cookie>
```

获取方式：
1. 浏览器登录 xueqiu.com
2. 按 F12 打开开发者工具 → Network 标签
3. 随意点击页面，找到任意一条 `xueqiu.com` 请求
4. 在 Request Headers 中找到 `Cookie` 字段，复制完整内容粘贴进来

> Cookie 有效期约 30 天，过期后重新获取。

### 2. LLM 服务商（必填，选其中一种）

在 `.env` 中取消对应选项的注释，填入 API Key：

| 服务商 | 注册地址 |
|--------|---------|
| DeepSeek | platform.deepseek.com |
| 智谱 AI | open.bigmodel.cn |
| Anthropic Claude | console.anthropic.com |
| 小米 / MiniMax / 月之暗面等 | 各服务商官网 |

填好后将 `AGENT_LAYER_ENABLED` 改为 `true`：

```
AGENT_LAYER_ENABLED=true
```

> 如果暂时没有 API Key，保持 `AGENT_LAYER_ENABLED=false` 也可运行，报告会缺少个股正宗度和综合结论部分。

---

## 如何触发使用

在 Claude Code 对话框中输入任意一句触发词：

```
启动早盘扫描
早盘热点
扫描市场
```

Claude Code 会自动调用 skill，运行完成后在 `reports/` 目录生成当日报告：

- `reports/YYYY-MM-DD-morning-scan.md` — 完整报告
- `reports/YYYY-MM-DD-morning-scan-brief.md` — 简报

---

## 常见失败原因

| 现象 | 原因 | 解决方法 |
|------|------|---------|
| 雪球数据为 0 条，提示 `cookie_expired` | 雪球 Cookie 已过期 | 重新从浏览器获取 Cookie 填入 `.env` |
| 雪球数据为 0 条，提示 `no_cookie` | `.env` 中未填 Cookie | 填写 `XUEQIU_COOKIE` |
| Agent 层跳过，报告缺少个股分析 | `AGENT_LAYER_ENABLED=false` 或 API Key 未填 | 检查 `.env` 中的 LLM 配置 |
| Agent 调用失败，提示余额不足 | LLM 服务商账户余额为零 | 充值后重试 |
| 美股数据拉取失败（ProxyError） | akshare 美股接口需直连，代理环境下可能失败 | 不影响主流程，A 股报告正常输出 |
| `stocks_dict.csv` 找不到 | 文件被移动或删除 | 确认该文件与 `run.py` 在同一目录 |
| 采集置信度为 `low` 或 `none` | 多个数据源采集失败 | 检查网络，稍后重试；报告仍会生成但准确性下降 |
