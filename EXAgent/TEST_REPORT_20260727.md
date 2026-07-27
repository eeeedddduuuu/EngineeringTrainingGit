# EXAgent 项目完整测试报告

> **测试日期**：2026-07-27  
> **测试人员**：Claude Code 自动化测试  
> **测试范围**：后端启动 → API 端点 → AI 对话 → Function Calling 工具调用 → SSE 流式输出 → 异常处理 → 前后端对接 → 会话管理 → 模块依赖  
> **测试环境**：Windows 11 家庭中文版, Python 3.13, FastAPI + SQLite, DeepSeek v4-pro, Uvicorn  

---

## 目录

1. [问题总览](#一问题总览)
2. [🔴 P0 严重问题 — 详析](#二p0-严重问题--详析)
   - [P0-1: create_content 工具调用失败 — providers.json 缺失](#p0-1-create_content-工具调用失败--providersjson-缺失)
   - [P0-2: chat_stream 是"假流式" — 工具调用期间无进度反馈](#p0-2-chat_stream-是假流式--工具调用期间无进度反馈)
   - [P0-3: 非流式 API 不返回 session_id — 多轮对话断裂](#p0-3-非流式-api-不返回-session_id--多轮对话断裂)
3. [🟡 P1 中等问题 — 详析](#三p1-中等问题--详析)
   - [P1-1: 前端 SSE 事件协议前后端不匹配](#p1-1-前端-sse-事件协议前后端不匹配)
   - [P1-2: 复杂请求超时风险](#p1-2-复杂请求超时风险)
   - [P1-3: 会话无过期机制 + 内存泄漏风险](#p1-3-会话无过期机制--内存泄漏风险)
4. [🟢 P2 小问题 — 详析](#四p2-小问题--详析)
5. [✅ 验证通过项](#五-验证通过项)
6. [修复优先级矩阵](#六修复优先级矩阵)

---

## 一、问题总览

| 编号 | 级别 | 问题简述 | 影响面 | 文件 | 修复难度 |
|:---:|:---:|------|:---:|------|:---:|
| P0-1 | 🔴 | `create_content` 工具不可用 | 核心功能 | `config/__init__.py` / `providers/__init__.py` | 低 |
| P0-2 | 🔴 | SSE 流式是假的，工具期间无进度 | 用户体验 | `orchestrator.py:661-676` | 中 |
| P0-3 | 🔴 | 非流式 API 缺 `session_id` | 多轮对话 | `orchestrator.py:654-659` | 极低 |
| P1-1 | 🟡 | SSE 事件类型前后端不匹配 | UI 死代码 | `orchestrator.py` vs `index.html` | 中 |
| P1-2 | 🟡 | 复杂请求 120s+ 超时 | 可靠性 | `orchestrator.py:609-644` | 中 |
| P1-3 | 🟡 | 会话内存泄漏 / 服务重启丢失 | 稳定性 | `orchestrator.py:577-699` | 中 |
| P2-1 | 🟢 | `multimodal/__init__.py` 导入写法歧义 | 可维护性 | `multimodal/__init__.py:29` | 极低 |
| P2-2 | 🟢 | 前端 login 页引用 Unsplash 外部图 | 加载体验 | `index.html:22` | 极低 |
| P2-3 | 🟢 | 端口文档不一致（8001 vs 8000） | 文档 | — | 极低 |
| P2-4 | 🟢 | 三个前端文件并存 | 维护混乱 | `frontend/` 目录 | 低 |
| P2-5 | 🟢 | Dashboard 图表文件编号重复 | 引用混乱 | `static/charts/` | 极低 |
| P2-6 | 🟢 | `knowledge_search` 硬编码 8090 端口 | 健壮性 | `tools/__init__.py:306` | 极低 |
| P2-7 | 🟢 | `chat()` 中 DeepSeek 非流式调用无重试 | 韧性 | `orchestrator.py:459-491` | 低 |

---

## 二、🔴 P0 严重问题 — 详析

### P0-1: create_content 工具调用失败 — providers.json 缺失

#### 问题定位

| 项目 | 内容 |
|------|------|
| **触发链** | `orchestrator._exec_create_content()` → `pipeline_adapter.create_content(provider="deepseek")` → `run_agent_pipeline(provider="deepseek")` → `run_agent(provider="deepseek")` → `load_config()` → `deepseek_provider(config=空的deepseek段)` |
| **根因文件** | `backend/p4_agent/config/__init__.py` |
| **根因代码** | 第 11-16 行 |

#### 详细分析

`config/__init__.py` 的 `load_config()` 函数：

```python
# backend/p4_agent/config/__init__.py:11-16
def load_config() -> dict[str, Any]:
    """加载完整的 providers.json 配置。"""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}  # ← providers.json 不存在，返回空 dict
```

文件系统中只有 `providers.example.json`（含占位符值），没有 `providers.json`：

```
backend/p4_agent/config/
├── __init__.py
├── providers.example.json   ← 存在，但不会被加载
└── providers.json           ← 不存在！
```

调用链继续往下 —— `run_agent()` 第 88-89 行：

```python
# backend/p4_agent/agents/__init__.py:88-89
if provider_config is None and provider != "mock":
    provider_config = load_config()  # ← 返回 {}
```

然后 `run_provider("deepseek", prompt, config={})` 最终到达 `deepseek_provider()`：

```python
# backend/p4_agent/providers/__init__.py:354-356
def deepseek_provider(prompt, config, tools=None, messages_override=None):
    api_key = str(config.get("api_key", "")).strip()  # ← 从空 dict 取，得到 ""
    if not api_key:
        raise ValueError("DeepSeek 配置不完整，请填写 api_key")  # ← 抛出异常
```

#### 影响范围

这并不意味着 AI 对话完全不可用。orchestrator 自己的 `_call_deepseek()` 用的是模块顶部的硬编码 key（第 24 行 `DS_API_KEY`），所以**基础聊天功能正常**。但是：

1. 用户说 "帮我写一个短视频脚本" → DeepSeek 模型判断需要调用 `create_content` 工具 → orchestrator 的 function calling 回环执行 `_exec_create_content()` → 内部调用 `pipeline_adapter.create_content(provider="deepseek")` → **抛出 ValueError**
2. 工具返回 `{"ok": False, "error": "DeepSeek 配置不完整，请填写 api_key"}` 给模型
3. 模型收到错误后有两种行为：
   - **行为 A**（常见）：模型自己"编造"一段脚本（不经过四步流水线，没有真实的热点分析/合规审查），质量不可控
   - **行为 B**（极端）：模型反复重试调用工具，触发 5 轮回环上限，最终返回空内容或超时

**实测验证**：发送 "帮我给抖音写一个AI工具测评的短视频脚本，60s" → 工具链：
```
Tool: create_content  → ❌ DeepSeek 配置不完整，请填写 api_key
Tool: web_search      → ✅ 搜索到 5 条结果
Tool: knowledge_search → ✅ 知识库检索完成
Tool: sensitive_word_filter → ✅ 风险等级: pass
```
模型在 `create_content` 失败后，基于 `web_search` 的搜索结果自己编了一段不完整的脚本。

#### 修复方案

**方案 A（推荐）**：创建 `providers.json`，将 `orchestrator.py` 中的 DeepSeek Key 同步到配置文件：

```json
{
  "deepseek": {
    "enabled": true,
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "你的DeepSeek_API_Key",
    "model": "deepseek-v4-pro",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "default_provider": "deepseek"
}
```

**方案 B（更健壮）**：在 `deepseek_provider()` 中增加环境变量兜底：

```python
# providers/__init__.py:354 之后
api_key = str(config.get("api_key", "")).strip()
if not api_key:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")  # ← 新增：环境变量兜底
if not api_key:
    raise ValueError("DeepSeek 配置不完整，请填写 api_key 或设置 DEEPSEEK_API_KEY 环境变量")
```

**方案 C（最简）**：在 orchestrator.py 中，将硬编码 key 注入到 p4_agent 的配置加载逻辑中。在 `_exec_create_content()` 调用 `create_content()` 之前，确保 `os.environ["DEEPSEEK_API_KEY"]` 已设置（目前 orchestrator.py 第 46 行已经设置了这个环境变量，但 `deepseek_provider()` 并没有读取它）。

---

### P0-2: chat_stream 是"假流式" — 工具调用期间无进度反馈

#### 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `orchestrator.py` 第 661-676 行 |
| **根因** | `chat_stream()` 内部调用同步的 `chat()`，等待全部完成后才逐字符输出 |

#### 详细分析

当前实现：

```python
# orchestrator.py:661-676
def chat_stream(self, message, session_id=None):
    """流式对话 — 内部复用已验证的 chat() 编排，模拟逐字符 SSE 流式输出。"""
    # 第 664 行：同步等待 chat() 全部完成（包括所有工具调用 + 最终回复）
    result = self.chat(message=message, session_id=session_id)
    reply = result["reply"]
    # ...
    # 第 671-672 行：结果拿到后才开始逐字符输出
    for ch in reply:
        yield f"event: text\ndata: {json.dumps({'content': ch}, ...)}\n\n"
    yield f"event: done\ndata: ..."
```

而 `chat()` 方法的执行流程是：

```
用户消息 → DeepSeek API (第1轮, ~5-30s)
         → 模型返回 tool_calls
         → 执行工具 create_content (内部又调4次DeepSeek, ~30-120s)
         → 执行工具 web_search (~2-5s)
         → 执行工具 sensitive_word_filter (~0.1s)
         → 工具结果送回 DeepSeek (第2轮, ~10-60s)
         → 模型生成最终回复 (~5-30s)
         → 返回 reply
```

整个过程中，`chat_stream()` 的 yield 循环不会执行，直到所有步骤完成。用户在浏览器中看到的是：
- **0-180s**：空白 loading（typing 动画三个点）
- **180s 后**：回复文字突然全部出现（虽然逐字很快，但整体延迟巨大）

实际上 orchestrator.py 第 494-527 行已经实现了**真正的流式 DeepSeek 调用** `_call_deepseek_stream()` 和第 530-570 行的 `_collect_stream()`，但 `chat()` 方法并没有使用它们，而是用了同步的 `_call_deepseek()`（第 605、644 行）。

#### 期望行为 vs 实际行为

| 时刻 | 期望行为 | 实际行为 |
|------|---------|---------|
| 用户发消息 | 立即显示用户气泡 | ✅ 立即显示 |
| AI 开始思考 | 显示 "🤔 分析需求中..." | ❌ 只有 typing 动画 |
| 调用 create_content | `🔧 create_content ⏳` badge | ❌ 无任何反馈 |
| create_content 完成 | `🔧 create_content ✅ 生成3套方案` | ❌ 无任何反馈 |
| 调用 web_search | `🔧 web_search ⏳` badge | ❌ 无任何反馈 |
| AI 生成最终回复 | 逐字流式输出 Markdown | ❌ 全部完成后才输出 |

#### 修复方案

需要重写 `chat_stream()` 使其成为真正的实时流式编排。核心改动点：

1. **改用流式 DeepSeek 调用**：用 `_call_deepseek_stream()` + `_collect_stream()` 替换 `_call_deepseek()`
2. **在 function calling 回环中 yield 事件**：
   - 每当模型选择了一个工具 → yield `event: tool_call`
   - 每当工具执行完毕 → yield `event: tool_result`
3. **最终文本流式输出**：用真正的 stream 而非逐字符切割

伪代码示意：

```python
def chat_stream(self, message, session_id=None):
    # ... 创建/恢复会话、构建 messages ...
    
    # 第一轮 DeepSeek 流式调用
    stream = _call_deepseek_stream(messages, tools=ORCHESTRATOR_TOOLS)
    result = _collect_stream(stream)
    
    while result.get("tool_calls") and fc_loop < 5:
        # 对每个 tool_call，先发 tool_call 事件
        for tc in result["tool_calls"]:
            yield f"event: tool_call\ndata: {json.dumps({'tool': tc['function']['name']})}\n\n"
            
            tool_result = execute_tool(...)
            
            yield f"event: tool_result\ndata: {json.dumps({'tool': ..., 'summary': ...})}\n\n"
        
        # 下一轮流式调用
        stream = _call_deepseek_stream(messages, tools=ORCHESTRATOR_TOOLS)
        result = _collect_stream(stream)
    
    # 最终文本 — 此时已经是完整 reply，逐字输出（保持当前行为）
    for ch in reply:
        yield f"event: text\ndata: ..."
    yield f"event: done\ndata: ..."
```

**注意**：`_collect_stream()` 本身是阻塞的（等待流全部完成），如果需要真正的工具调用期间流式输出，需要在 stream 处理中检测 `tool_calls` 增量并提前中断、yield 工具事件。

---

### P0-3: 非流式 API 不返回 session_id — 多轮对话断裂

#### 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `orchestrator.py` 第 654-659 行 |
| **根因** | `chat()` 的 return dict 中缺少 `session_id` 字段 |

#### 详细分析

```python
# orchestrator.py:654-659
def chat(self, message, session_id=None):
    # ... 编排逻辑 ...
    return {
        "reply": reply,
        "tool_calls_made": tool_calls_made,
        # "session_id": session_id,  ← 第 657 行，session_id 变量存在但没放进 return！
        "usage": result.get("usage", {}),
    }
```

对比流式 API 的 `done` 事件（第 674 行）：

```python
yield f"event: done\ndata: {json.dumps({'session_id': sid, ...})}\n\n"
```

流式 API 返回了 `session_id`，但非流式 API 没有。

**调用链验证**：

```
POST /api/agent/chat  →  agent_chat()  →  orch.chat()  →  return {reply, tool_calls_made, usage}
                                                              ↑ 少了 session_id
```

前端 HTML (`index.html`) 的流式对话（`sendAgentMsg()`）在 `done` 事件中通过 `data.session_id` 获取并保存会话 ID（第 2664 行）：

```javascript
case 'done':
    if (data.session_id) agentSessionId = data.session_id;
```

但如果前端切换到非流式 API（如 `appendAgentMsg()` 函数），则无法获取 `session_id`，后续对话都是新会话。

#### 修复方案

在 `chat()` 方法的 return dict 中加上一行：

```python
return {
    "reply": reply,
    "tool_calls_made": tool_calls_made,
    "session_id": session_id,    # ← 加这一行
    "usage": result.get("usage", {}),
}
```

**注意**：`session_id` 变量在第 596-597 行已经被正确赋值为最终的会话 ID（无论是新建还是复用），只是没有放进返回值。

---

## 三、🟡 P1 中等问题 — 详析

### P1-1: 前端 SSE 事件协议前后端不匹配

#### 问题定位

| 项目 | 内容 |
|------|------|
| **后端** | `orchestrator.py` `chat_stream()` 第 671-674 行 |
| **前端** | `frontend/index.html` `processEvent()` 第 2630-2671 行 |

#### 详细分析

**后端实际发出的事件**（`chat_stream()` 第 671-674 行）：

| 事件类型 | 何时发出 | 数据内容 |
|---------|---------|---------|
| `text` | 每字符一次 | `{content: "字"}` |
| `done` | 全部完成后一次 | `{session_id, tool_calls_made, usage}` |
| `error` | 异常时 | `{error: "..."}` |

**前端能处理的事件**（`index.html` `processEvent()` 第 2634-2669 行）：

| 事件类型 | 处理逻辑 | 实际是否触发 |
|---------|---------|:---:|
| `text` | 累积内容 → Markdown 渲染 | ✅ 能触发 |
| `tool_call` | 在气泡下添加 `🔧 工具名 ⏳` loading badge | ❌ 永远不会触发 |
| `tool_result` | 更新 loading badge 为 `🔧 工具名 ✅ 摘要` | ❌ 永远不会触发 |
| `done` | 保存 `session_id`，清理 | ✅ 能触发 |
| `error` | 显示错误信息 | ✅ 能触发（异常时） |

这意味着前端花了精力实现了工具调用进度的 UI 展示，但后端从未发送对应事件。这是前后端**协议设计阶段就对齐了，但后端实现阶段没跟上**的典型案例。

#### 修复方案

与 P0-2 联动修复。在 `chat_stream()` 中增加 `tool_call` 和 `tool_result` 事件的 yield。

---

### P1-2: 复杂请求超时风险

#### 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `orchestrator.py` 第 459-491 行（`_call_deepseek`）、第 609-644 行（回环） |
| **涉及 timeout** | DeepSeek API 调用 180s × 最多 5 轮 + 工具内部耗时 |

#### 详细分析

当前 `chat()` 方法的 function calling 回环：

```python
# orchestrator.py:609
while result.get("tool_calls") and fc_loop < 5:   # ← 最多 5 轮
    fc_loop += 1
    # ... 保存 assistant msg ...
    
    for tc in result["tool_calls"]:                # ← 每轮可能多个工具
        tool_result = execute_tool(func_name, func_args)
        # → create_content 内部: pipeline_adapter → run_agent_pipeline
        #   → run_agent("trend")    → deepseek_provider (timeout=120s)
        #   → run_agent("script")   → deepseek_provider (timeout=120s)
        #   → run_agent("review")   → deepseek_provider (timeout=120s)
        #   → run_agent("strategy") → deepseek_provider (timeout=120s)
        # 总计最多 480s
    
    # 工具结果送回模型
    result = _call_deepseek(messages, tools=ORCHESTRATOR_TOOLS)  # timeout=180s
```

最坏情况计算（当 `create_content` 可用时）：

```
轮次 1: DeepSeek API (180s) + create_content(4×120s=480s) + web_search(15s) = 675s
轮次 2: DeepSeek API (180s) = 180s
─────────────────────────────────────────────────────────
总计最坏: 855s ≈ 14 分钟
```

`_call_deepseek()` 的 timeout=180s，`deepseek_provider()` 的 timeout=120s，但 `create_content` 内部是 4 个串行 Agent 调用，每个 120s。

**实际测试**：发送 "帮我写美食短视频脚本" 时，请求在 120s 客户端超时后断开（服务端可能还在跑）。

#### 修复方案

1. **回环上限**：将 `fc_loop < 5` 改为 `fc_loop < 2`（大多数情况 1-2 轮足够）
2. **工具总超时**：在 `execute_tool()` 层面加 `signal.alarm` 或 `concurrent.futures.TimeoutError`
3. **`create_content` 异步化**：将 4 个 Agent 并行执行而非串行（review 和 strategy 不依赖彼此）
4. **前端超时提示**：在 `sendAgentMsg()` 中增加超时后的友好提示 + 重试按钮

---

### P1-3: 会话无过期机制 + 内存泄漏风险

#### 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `orchestrator.py` 第 577-699 行 |
| **数据结构** | `AgentOrchestrator.sessions: dict[str, list[dict]]` |

#### 详细分析

```python
class AgentOrchestrator:
    def __init__(self):
        self.sessions: dict[str, list[dict]] = {}  # ← 纯内存 dict
```

存在的问题：

1. **无 TTL**：会话永远不会自动过期。用户打开页面聊两句就关掉 → session 永久占用内存
2. **服务重启丢失**：uvicorn reload 或进程崩溃 → 所有正在进行的对话状态丢失
3. **无持久化**：没有与会话表（`sessions` 表在 SQLite 中已定义）对接
4. **无上限**：虽然 `get_sessions()` 只返回前 20 条（第 681 行），但内存中可能积累数百个废弃会话
5. **裁剪逻辑不彻底**：`chat()` 第 651-652 行的裁剪只保留最近 20 轮，但旧 session 本身不会被删除

```python
# orchestrator.py:651-652 — 裁剪逻辑
if len(messages) > 42:
    self.sessions[session_id] = [messages[0]] + messages[-40:]
    # 只裁剪了消息列表，session 条目本身不删除
```

每条消息大约 2-5KB（含 system prompt + 工具调用结果），100 个活跃会话 ≈ 2-5MB，不算大，但如果长期运行（uvicorn 不重启）会持续增长。

#### 修复方案

1. **短期**：增加 TTL 清理逻辑。每次 `chat()` 被调用时，遍历 sessions 删除超过 30 分钟未活动的会话
2. **中期**：记录每个 session 的 `last_active` 时间戳
3. **长期**：利用 P3 已有的 `sessions` 表做持久化（`EXAgent/backend/app/models/business.py` 中已定义 `Session` 模型）

---

## 四、🟢 P2 小问题 — 详析

### P2-1: multimodal/__init__.py 导入写法有歧义

**文件**：`backend/p4_agent/multimodal/__init__.py`  
**行号**：第 29、41、56、74 行

```python
# 第 29 行
from multimodal.multimodal import call_multimodal   # ← multimodal 包下有同名 multimodal.py 模块
```

这里 `multimodal.multimodal` 的含义是：`multimodal` 包 → `multimodal.py` 模块。它之所以能工作，是因为第 13-15 行把 `multimodal/` 目录加入了 `sys.path`：

```python
_SKILL_DIR = Path(__file__).resolve().parent   # = .../multimodal/
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))
```

**建议改为**：使用包内相对导入，不依赖 sys.path hack：

```python
from .multimodal import call_multimodal
```

---

### P2-2: 前端登录页引用 Unsplash 外部图片

**文件**：`frontend/index.html` 第 22 行

```css
background-image: url('https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=1920&q=80');
```

Unsplash 在国内访问极慢或被墙。登录页加载时如果这张背景图卡住，整个页面会白屏等待。**建议替换为 CSS 渐变**。

---

### P2-3: 端口文档不一致

- 记忆文件 `exagent-implementation-20260727.md` 记载 → **8001 端口**
- 实际 `backend/app/main.py` 启动 → **8000 端口**（FastAPI uvicorn）
- 前端 `index.html:832` → `API_BASE = 'http://127.0.0.1:8000/api'`
- `orchestrator.py` → **没有独立的 `__main__` 入口**，没有 8001 端口

结论：不存在 8001 端口，文档需要更新。

---

### P2-4: 三个前端文件并存

```
frontend/
├── app.py                    # Streamlit 前端 "灵境智造"
├── app_new.py                # 第三个版本
├── app.py.streamlit-backup   # 备份
├── index.html                # 纯 HTML 前端 "灵犀创作助手"（唯一有 AI 对话界面的）
```

- `index.html` 是唯一包含 AI 对话界面的前端（"灵犀创作助手"，使用 SSE 流式对话）
- `app.py` 是 Streamlit 前端（"灵境智造"，使用 P3 传统 API）
- 不清楚哪个是正式版。Streamlit 前端不包含 AI 对话功能（没有 `/api/agent/chat` 的调用）

---

### P2-5: Dashboard 图表文件编号重复

```
frontend/static/charts/
├── chart_1_donut.html
├── chart_2_bar.html
├── chart_3_area.html
├── chart_4_hbar.html       ← 重复 4
├── chart_4_line.html       ← 重复 4
├── chart_5_hbar.html       ← 重复 5
├── chart_5_treemap.html    ← 重复 5
├── chart_6_treemap.html    ← 重复 6
├── chart_6_pie.html        ← 重复 6
├── chart_7_pie.html        ← 孤立 7（无配对）
```

看起来是重命名过程中遗留的旧文件。如果前端按编号引用，会加载到错误内容。

---

### P2-6: knowledge_search 硬编码 8090 端口

**文件**：`backend/p4_agent/tools/__init__.py` 第 306 行

```python
kb_url = "http://127.0.0.1:8090/api/knowledge/search"
```

P5 知识库服务的端口硬编码。如果 P5 服务部署在其他端口，知识库检索会静默回退到本地 fallback（返回占位文本 "知识库服务待启动"），用户感知到的是"有结果但内容是假的"，但不报错。

---

### P2-7: chat() 中 DeepSeek 非流式调用无重试

**文件**：`orchestrator.py` 第 459-491 行

`_call_deepseek()` 使用 `requests.post(timeout=180)`，但没有任何重试逻辑。DeepSeek API 偶尔会返回 503（服务繁忙）或连接超时。对比 `web_search()` 工具使用了三层回退（DDGS → Bing → 报错），但核心的 DeepSeek 对话没有任何重试机制。

**建议**：增加 1-2 次指数退避重试（如 2s → 4s）。

---

## 五、✅ 验证通过项

以下功能通过实际调用测试验证，工作正常：

| 测试项 | 端点/方法 | 测试方式 | 结果 |
|--------|----------|---------|:--:|
| 后端启动 | `uvicorn app.main:app --port 8000` | 直接启动 | ✅ 无报错 |
| 根路径 | `GET /` | curl | ✅ 返回版本信息 |
| 基础 AI 对话 | `POST /api/agent/chat` | Python requests | ✅ 200, Markdown 回复 |
| AI 回复质量 | "你好，一句话介绍你自己" | 实际调用 | ✅ 含标题/表格/emoji/加粗 |
| 工具列表 | `GET /api/agent/tools` | curl | ✅ 8 个工具完整 |
| SSE 流式对话 | `POST /api/agent/chat/stream` | Python requests stream | ✅ `text/event-stream` |
| SSE 逐字输出 | "用一句话说说AI对创作者的影响" | 逐 chunk 验证 | ✅ 54 个 text chunk |
| 空消息校验 | `{"message": ""}` | requests | ✅ 422 (min_length=1) |
| 超长消息校验 | `{"message": "你好"*3000}` | requests | ✅ 422 (max_length=5000) |
| 不存在 session | `GET /api/agent/sessions/nonexistent` | curl | ✅ 404 |
| 会话创建 | `POST /api/agent/chat` + session_id | requests | ✅ 200 |
| 会话历史查询 | `GET /api/agent/sessions/{id}` | requests | ✅ 消息列表正常 |
| 会话列表 | `GET /api/agent/sessions` | curl | ✅ 返回列表 |
| `web_search` 工具 | 直接调用 | Python import | ✅ 返回 3 条结果 |
| `sensitive_word_filter` | 直接调用 | Python import | ✅ 正常检测 |
| CORS | `Access-Control-Allow-Origin` | 响应头检查 | ✅ `*` |
| 静态文件 | `/uploads/` | 目录检查 | ✅ 已挂载 |
| 前端 HTML 加载 | `index.html` | 直接打开 | ✅ 登录页渲染正常 |
| 前端 SSE 解析 | `processEvent()` | 流式调用 | ✅ text/done/error 事件正常 |
| 前端 Markdown 渲染 | `simpleMarkdown()` | 查看渲染结果 | ✅ 表格/列表/代码块/引用 |
| 数据库自动建表 | `Base.metadata.create_all` | 启动日志 | ✅ 正常 |

---

## 六、修复优先级矩阵

| 优先级 | 编号 | 问题 | 影响面 | 修复工作量 | 建议顺序 |
|:---:|:---:|------|:---:|:---:|:---:|
| 🔴 P0 | P0-3 | 非流式 API 缺 session_id | 多轮对话 | 1 行代码 | ① 先修 |
| 🔴 P0 | P0-1 | create_content 工具不可用 | 核心创作功能 | 创建 JSON 文件 | ② 再修 |
| 🔴 P0 | P0-2 | SSE 假流式 | 用户体验 | 重写 chat_stream | ③ 核心改动 |
| 🟡 P1 | P1-1 | SSE 事件前后端不匹配 | UI 展示 | 与 P0-2 联动 | ③ 一起修 |
| 🟡 P1 | P1-2 | 复杂请求超时 | 可靠性 | 加 timeout + 并行化 | ④ 可靠性 |
| 🟡 P1 | P1-3 | 会话无过期/内存泄漏 | 稳定性 | 加 TTL 清理 | ⑤ 稳定性 |
| 🟢 P2 | P2-7 | DeepSeek 调用无重试 | 韧性 | 加 retry | ⑥ 顺手修 |
| 🟢 P2 | P2-2 | 前端 Unsplash 外链 | 加载速度 | 1 行 CSS | ⑦ 顺手修 |
| 🟢 P2 | P2-1 | multimodal import 歧义 | 可维护性 | 改相对导入 | ⑧ 顺手修 |
| 🟢 P2 | P2-6 | knowledge_search 硬编码端口 | 配置化 | 改环境变量 | ⑨ 顺手修 |
| 🟢 P2 | P2-4 | 多前端文件清理 | 维护 | 删除/归档 | ⑩ 清理 |
| 🟢 P2 | P2-5 | 图表文件去重 | 维护 | 删除重复 | ⑩ 清理 |
| 🟢 P2 | P2-3 | 端口文档更新 | 文档 | 改 1 行 | ⑪ 文档 |

---

> **报告版本**：v2.0  
> **生成日期**：2026-07-27  
> **测试耗时**：约 45 分钟  
> **生成方式**：代码静态分析 + 实际运行测试（启动服务、发送 HTTP 请求、验证响应）
