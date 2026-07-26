# P3 后端 — 部署与启动指南

## 环境要求

| 项目 | 版本 |
|------|------|
| Python | ≥ 3.10 |
| pip | ≥ 23.0 |
| 操作系统 | Windows / Linux / macOS |

## 快速启动

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库（建表 + 导入 158 条知识库样本）
python init_db.py

# 4. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 测试账号

| 用户名 | 密码 | 说明 |
|--------|------|------|
| `p3test` | `123456` | P3 开发测试账号 |
| `test2` | `123456` | 备用测试账号 |

## API 端点（18 个）

### 认证
| 方法 | 路径 | 说明 | JWT |
|------|------|------|:--:|
| POST | `/api/auth/register` | 用户注册 | — |
| POST | `/api/auth/login` | 用户登录 → 返回 JWT | — |
| GET | `/api/auth/me` | 获取当前用户信息 | ✅ |

### 创作
| 方法 | 路径 | 说明 | JWT |
|------|------|------|:--:|
| POST | `/api/creation/start` | 提交创作任务 | ✅ |
| GET | `/api/task/{task_id}/status` | 轮询任务状态 | ✅ |
| POST | `/api/creation/upload` | 上传素材文件 | ✅ |
| GET | `/api/creation/uploads` | 列出已上传文件 | ✅ |
| DELETE | `/api/creation/uploads/{file_id}` | 删除已上传文件 | ✅ |

### 方案
| 方法 | 路径 | 说明 | JWT |
|------|------|------|:--:|
| GET | `/api/schemes?session_id=` | 获取会话全部方案 | ✅ |
| GET | `/api/scheme/{id}` | 获取单方案详情 | ✅ |
| POST | `/api/schemes/compare` | A/B 方案对比 | ✅ |

### 历史与导出
| 方法 | 路径 | 说明 | JWT |
|------|------|------|:--:|
| GET | `/api/history?page=&size=` | 分页历史记录 | ✅ |
| GET | `/api/export/{id}?format=md` | 导出 Markdown | ✅ |
| GET | `/api/export/{id}?format=docx` | 导出真正的 .docx | ✅ |

### 知识库与统计
| 方法 | 路径 | 说明 | JWT |
|------|------|------|:--:|
| GET | `/api/knowledge/search?q=&top_k=` | 向量检索知识库 | ✅ |
| GET | `/api/stats/samples` | 样本统计数据 | ✅ |

### 审核
| 方法 | 路径 | 说明 | JWT |
|------|------|------|:--:|
| POST | `/api/review` | 提交审核 | ✅ |
| PUT | `/api/review/{id}` | 修改审核结果 | ✅ |

## 目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口，路由注册 + 启动建表
│   ├── config.py            # 配置（JWT_SECRET, HF_ENDPOINT 等）
│   ├── database.py          # SQLAlchemy 引擎 + Session
│   ├── models/              # 数据模型（6 张表）
│   │   ├── user.py          # User
│   │   └── business.py      # Session / Scheme / AgentLog / KnowledgeItem / Review
│   ├── routers/             # 路由（8 个模块）
│   │   ├── auth.py          # 认证（register/login/me）
│   │   ├── creation.py      # 创作（start/status/upload）
│   │   ├── schemes.py       # 方案（列表/详情/对比）
│   │   ├── history.py       # 历史记录
│   │   ├── export_routes.py # 导出（Markdown + 真正的 .docx）
│   │   ├── stats.py         # 统计
│   │   ├── knowledge.py     # 向量检索
│   │   └── review.py        # 审核
│   ├── schemas/             # Pydantic 数据校验（7 个模块）
│   ├── services/            # 知识库服务（Chroma + bge-small-zh-v1.5）
│   └── utils/               # 工具（security + deps）
├── p4_agent/                # P4 Agent 模块
│   ├── agents/              # 4 个 Agent（Trend/Script/Review/Strategy）
│   ├── providers/           # LLM Provider（DeepSeek/Coze/Mock）
│   ├── tools/               # 工具函数
│   ├── workflow/            # 工作流引擎
│   ├── prompts/             # YAML Prompt 模板
│   └── coze_workflows/      # Coze 平台配置
├── prompts/                 # Agent Prompt 文件
├── uploads/                 # 用户上传素材目录
├── init_db.py               # 数据库初始化 + 种子数据
├── requirements.txt         # Python 依赖
└── app.db                   # SQLite 数据库文件
```

## Agent 模式切换

编辑 `backend/app/routers/creation.py` 第 186 行：

```python
PROVIDER = "deepseek"   # 真实 LLM（需 API Key）
PROVIDER = "mock"       # 离线 Mock（默认，开箱即用）
PROVIDER = "coze"       # Coze 平台
```

## 数据库

- **类型**: SQLite
- **文件**: `backend/app.db`
- **重建**: 删除 `app.db` → `python init_db.py`

### 表结构

| 表 | 行数 | 说明 |
|----|:--:|------|
| users | 3 | 用户账号 |
| sessions | 4+ | 创作会话 |
| schemes | 12+ | 方案（A/B/C × N 次） |
| agent_logs | 0+ | Agent 调用日志 |
| reviews | 0+ | 审核记录 |
| knowledge_items | 158 | 知识库样本 |

## 常见问题

**Q: `ModuleNotFoundError: No module named 'app'`**
A: 确保在 `backend/` 目录下运行，或设置 `PYTHONPATH=backend`

**Q: Chroma / SentenceTransformer 加载卡住**
A: 首次运行需下载 `bge-small-zh-v1.5` 模型（~100MB），等待几分钟即可

**Q: Word 导出报 500**
A: 确保安装 `python-docx`：`pip install python-docx`
