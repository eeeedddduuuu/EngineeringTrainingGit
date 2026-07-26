# Coze 工作流导入说明

## 概述

本项目使用 Coze 扣子平台作为题目 3 的 Agent 运行平台。需要在 Coze 中创建 **4 个 Bot**（一个 Agent = 一个 Bot），然后在 `providers.json` 中填入各自的 Bot ID。

## 第一步：获取 Coze API Token

1. 打开 [Coze 扣子](https://www.coze.cn)
2. 进入 **个人设置 → API 令牌**
3. 创建新 Token，复制备用

## 第二步：创建 4 个 Bot（核心步骤）

Coze 不支持直接导入工作流 JSON，但每个 Bot 的配置内容已准备好，**手动创建只需 5 分钟/个**。

### 2.1 创建趋势分析 Agent Bot

1. Coze 首页 → **新建 Bot** → 名称填 `趋势分析Agent`
2. **角色与回复**（核心）→ 粘贴下面「trend_agent_system_prompt.txt」的完整内容
3. **工具/插件**（可选）→ 添加：
   - 🔍 必应搜索（内置插件）
   - 🕐 时间查询（如需）
4. **模型选择** → 推荐 `DeepSeek-R1` 或 `豆包`
5. 点击 **发布** → 记录 Bot ID

### 2.2 创建脚本创作 Agent Bot

1. Coze 首页 → **新建 Bot** → 名称填 `脚本创作Agent`
2. **角色与回复** → 粘贴「script_agent_system_prompt.txt」
3. **无需插件**（这是纯 LLM 生成型 Agent）
4. **模型选择** → 推荐 `DeepSeek-V3` 或 `豆包`
5. 发布 → 记录 Bot ID

### 2.3 创建合规审查 Agent Bot

1. Coze 首页 → **新建 Bot** → 名称填 `合规审查Agent`
2. **角色与回复** → 粘贴「review_agent_system_prompt.txt」
3. **工具/插件** → 无需（规则在 Prompt 中）
4. **模型选择** → 推荐 `DeepSeek-R1`（推理更严谨）
5. 发布 → 记录 Bot ID

### 2.4 创建发布策略 Agent Bot

1. Coze 首页 → **新建 Bot** → 名称填 `发布策略Agent`
2. **角色与回复** → 粘贴「strategy_agent_system_prompt.txt」
3. **工具/插件** → 无需（策略分析型）
4. **模型选择** → 推荐 `DeepSeek-V3`
5. 发布 → 记录 Bot ID

## 第三步：修改配置

编辑 `backend/p4_agent/config/providers.json`，填入实际值：

```json
{
  "coze": {
    "enabled": true,
    "base_url": "https://api.coze.cn/open_api/v2/chat",
    "token": "pat_xxxxxxxxxxxxx",
    "bot_ids": {
      "trend":     "1234567890123456",
      "script":    "1234567890123457",
      "review":    "1234567890123458",
      "strategy":  "1234567890123459"
    },
    "user": "p4-agent",
    "description": "Coze 4 Bot 已就绪"
  },
  "default_provider": "coze"
}
```

## 第四步：测试

```bash
cd backend/p4_agent
python main.py --provider coze --mode single
```

成功时输出包含 `provider: coze` 和 Coze 返回的脚本方案。
