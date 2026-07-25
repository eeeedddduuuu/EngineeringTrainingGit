# P4 Agent 模块 — 工程实训项目

## 模块简介

面向游戏策划、短视频创作、社交媒体运营等场景，基于 Coze/Dify/DeepSeek 的 AI Agent 数字媒体创作平台。支持输入主题、受众、平台、时长、风格，自动生成脚本、分镜、封面文案和发布策略。

## 目录结构

```
p4-agent/
├── agents/         # 4 个专业 Agent (trend/script/review/strategy)
├── tools/          # 5 个模拟工具 (Search/Memory/ErrorReporter/TemplateMatcher/SensitiveFilter)
├── providers/      # Provider 适配层 (Mock/DeepSeek/Coze/Dify)
├── prompts/        # Prompt 模板 (4 个 YAML 文件)
├── workflow/       # 工作流编排 + 评分算法
├── config/         # Provider 配置
├── parser/         # Markdown → JSON 解析器
├── main.py         # CLI 入口 & 演示脚本
├── pipeline_adapter.py  # Pipeline 外部调用封装
├── outputs/        # Agent 调用日志 & 输出
└── requirements.txt
```

## 集成状态 (Day 2)

| 项目 | 状态 |
|------|:--:|
| P3 `feature/backend` 已集成 `backend/p4_agent/` | ✅ 18 个文件完全一致 |
| 4 个 YAML Prompt 模板 | ✅ v1 最新版 |
| Mock 模式可跑通 | ✅ `python main.py --mode all` |
| `create_content()` 一行调用 | ✅ P3 已对接 `creation.py` |
| `feature/agent` 原始分支 | 📌 不再合并，以 P3 集成为准 |

> **核实结论 (2026-07-25)**：P3 在 `origin/feature/backend` 中集成的 `backend/p4_agent/` 与 `feature/agent` 中的 `p4-agent/` **18 个文件逐字节一致**，无需任何更新。原始 `feature/agent` 分支保留作参考，后续开发以 P3 集成为准。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 单 Agent 验证
python main.py --mode single

# 3. 完整流水线
python main.py --mode pipeline

# 4. 方案评分
python main.py --mode scoring
```

## 小组分工

| 角色 | 分支 | 负责人 |
|------|------|--------|
| P1 产品/PM | feature/docs | — |
| P2 前端开发 | feature/frontend | — |
| P3 后端开发 | feature/backend | — |
| P4 Agent开发 | feature/agent | 罗欢 |
| P5 数据/测试 | feature/data-kb | — |
