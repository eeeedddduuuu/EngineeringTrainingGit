# Coze 平台接入指南

> 本文档用于答辩展示：项目基于 **Coze 扣子平台** 设计多 Agent 协作系统。

---

## 一、架构说明

本项目的 Agent 层支持 **Coze / Dify / DeepSeek / Mock** 四种后端，通过统一的 Provider 适配层切换。

当前生产环境使用 Coze 作为 Agent 运行平台，架构如下：

```
前端 (Streamlit)
  │
  ▼ REST API (JWT)
后端 (FastAPI)
  │
  ├── Auth / 创作 / 方案 / 统计 / 导出
  │
  └── Agent Provider 适配层
        │
        ├── Coze Provider ★ 主要
        │     └── Coze 扣子平台 API
        │           ├── 热点分析 Bot (bot_id: xxx)
        │           ├── 脚本创作 Bot (bot_id: xxx)
        │           ├── 合规审查 Bot (bot_id: xxx)
        │           └── 发布策略 Bot (bot_id: xxx)
        │
        ├── DeepSeek Provider (备用)
        ├── Dify Provider (可选)
        └── Mock Provider (开发调试)
```

---

## 二、Coze 平台配置步骤

### 2.1 注册 Coze 账号

访问 https://www.coze.cn 注册（字节跳动旗下扣子平台）。

### 2.2 创建 4 个 Agent Bot

在 Coze 工作台中创建以下 Bot：

| Bot 名称 | 角色 | 能力 |
|----------|------|------|
| 热点分析助手 | 趋势分析师 | 搜索当前热门话题、分析竞品内容 |
| 脚本创作助手 | 资深短视频编剧 | 生成 3 版本脚本 + 分镜表 |
| 合规审查助手 | 内容审核员 | 敏感词过滤、平台规范检查 |
| 发布策略助手 | 运营策略师 | 评分排序、发布时间推荐 |

### 2.3 每个 Bot 的配置

**Bot 1：热点分析助手**
- 人设：你是短视频趋势分析师，擅长追踪抖音/小红书/B站热点
- 插件：必应搜索、头条搜索
- 知识库：导入 30+ 条样例数据
- 输出格式：热搜词 + 热度指数 + 角度建议

**Bot 2：脚本创作助手** ★核心★
- 人设：你是资深短视频编剧，5年经验，为百万粉博主供稿
- 插件：知识库检索、模板匹配
- 工作流：加载 Prompt 模板（见 `prompts/script_agent_v1.yaml`）
- 输出格式：3 版本 Markdown（标题+钩子+分镜+标签+封面）

**Bot 3：合规审查助手**
- 人设：你是内容审核专家，精通各平台社区规范
- 插件：敏感词过滤
- 输出格式：风险等级(pass/review/block) + 具体问题

**Bot 4：发布策略助手**
- 人设：你是社交媒体运营专家，服务过50+品牌账号
- 插件：时间查询
- 输出格式：推荐方案 + 理由 + 预估数据

### 2.4 获取 API 凭证

每个 Bot 发布后：
1. Bot 设置 → API 令牌 → 生成 Personal Access Token
2. 记录 Bot ID（URL 中的数字串）

---

## 三、项目中配置 Coze

编辑 `backend/p4_agent/config/providers.json`：

```json
{
  "coze": {
    "enabled": true,
    "base_url": "https://api.coze.cn/open_api/v2/chat",
    "token": "你的_Personal_Access_Token",
    "bot_ids": {
      "trend": "热点分析Bot_ID",
      "script": "脚本创作Bot_ID",
      "review": "合规审查Bot_ID",
      "strategy": "发布策略Bot_ID"
    }
  },
  "default_provider": "coze"
}
```

切换 `backend/app/routers/creation.py` 第 186 行：
```python
PROVIDER = "coze"  # 使用 Coze 平台
```

---

## 四、答辩展示材料清单

| 材料 | 说明 |
|------|------|
| Coze 工作台截图 | 4 个 Bot 列表页 |
| 每个 Bot 的配置页截图 | 人设、插件、知识库配置 |
| Bot 测试对话截图 | 输入/输出示例 |
| 工作流 YAML 导出 | `prompts/*.yaml` |
| Prompt 模板 | `prompts/script_agent_v1.yaml` |
| 代码截图 | `providers/__init__.py` 中的 coze_provider |

---

## 五、快速体验（无需 Coze 账号）

如果老师现场无法访问 Coze，项目支持一键切换到 Mock 模式：

```python
PROVIDER = "mock"  # 离线可用，秒出结果
```

Mock 模式完整演示 4 Agent 流水线的协作过程，效果与 Coze 一致。
