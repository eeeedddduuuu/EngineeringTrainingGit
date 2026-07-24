# AI 数字媒体创作助手 — 工程实训项目

## 项目简介

面向游戏策划、短视频创作、社交媒体运营等场景，基于 Coze/Dify/DeepSeek 的 AI Agent 数字媒体创作平台。支持输入主题、受众、平台、时长、风格，自动生成脚本、分镜、封面文案和发布策略。

## 技术栈

- **后端**: Python + FastAPI
- **前端**: Streamlit
- **Agent**: LangChain + Dify + Coze + DeepSeek API
- **数据库**: MySQL + SQLAlchemy
- **知识库**: ChromaDB + nomic-embed-text (Embedding)
- **工具**: Web Search, Knowledge Retrieval, Sensitive Word Filter, Template Matcher

## 项目结构

```
Final/
├── backend/        # P3 FastAPI 后端
├── frontend/       # P2 Streamlit 前端
├── agents/         # P4 Agent 模块
├── tools/          # P4 工具模块
├── providers/      # P4 Provider 适配层
├── prompts/        # P4 Prompt 模板
├── workflow/       # P4 工作流编排
├── knowledge_base/ # P5 知识库
├── docs/           # P1 文档
├── tests/          # P5 测试
└── outputs/        # Agent 调用日志 & 输出
```

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动后端
cd backend && python app.py

# 3. 启动前端
cd frontend && streamlit run app.py
```

## 小组分工

| 角色 | 分支 | 负责人 |
|------|------|--------|
| P1 产品/PM | feature/docs | — |
| P2 前端开发 | feature/frontend | — |
| P3 后端开发 | feature/backend | — |
| P4 Agent开发 | feature/agent | 罗欢 |
| P5 数据/测试 | feature/data-kb | — |
