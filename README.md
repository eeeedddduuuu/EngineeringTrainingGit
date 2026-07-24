# AI 数字媒体创作助手

## 项目简介

面向短视频创作者、游戏策划、社交媒体运营的 AI Agent 系统。用户输入主题、受众、平台、时长和风格，系统通过多 Agent 协作自动生成多版本脚本、分镜表、封面文案和发布策略。

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | Streamlit |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| Agent | LangChain + Coze/Dify |
| 知识库 | Chroma + text-embedding |
| 大模型 | DeepSeek API |
| 数据 | Pandas + Plotly |

## 快速启动

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
pip install streamlit requests
streamlit run app.py
```

## 项目结构

```
EngineeringTrainingGit/
├── frontend/            # Streamlit 前端
│   ├── app.py
│   ├── pages/
│   └── utils/
├── backend/             # FastAPI 后端
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   └── utils/
│   └── prompts/         # Agent Prompt 模板
├── data/                # 数据 & 知识库
│   ├── samples/
│   └── knowledge_base/
├── docs/                # 文档
└── tests/               # 测试
```

## 团队

| 角色 | 职责 |
|------|------|
| PM | 需求、架构、进度、报告、答辩 |
| 前端 | Streamlit 页面开发 |
| 后端 | FastAPI + 数据库 + API |
| Agent | LangChain/Coze 工作流编排 |
| 数据/测试 | 知识库、样例数据、全流程测试 |
