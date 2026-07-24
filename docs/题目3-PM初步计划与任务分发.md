# PM 初步计划与任务分发 — Day 1

> **Git 仓库：** https://github.com/eeeedddduuuu/EngineeringTrainingGit
> **PM：** [你的名字]
> **项目：** 题目3 — 基于 Coze/Dify 的 AI 数字媒体创作助手
> **总工期：** 4 天

---

## 一、Day 1 上午 — PM 自己先完成的事（2h）

> 这些是 PM 独立完成或在组员到位前准备好的，不需要等任何人。

### 1.1 初始化 Git 仓库（30min）

```bash
# 1. 克隆仓库
git clone https://github.com/eeeedddduuuu/EngineeringTrainingGit
cd EngineeringTrainingGit

# 2. 创建 develop 分支
git checkout -b develop
git push -u origin develop

# 3. 在 develop 上创建初始项目结构
mkdir -p frontend
mkdir -p backend/app/{routers,models,schemas,utils}
mkdir -p backend/prompts
mkdir -p data/{samples,knowledge_base}
mkdir -p docs
mkdir -p tests

# 4. 写 .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.env
venv/
.venv/
node_modules/
uploads/
*.db
*.sqlite3
.DS_Store
EOF

# 5. 写 README.md 草稿
cat > README.md << 'EOF'
# AI 数字媒体创作助手

## 项目简介
面向短视频创作、社交媒体运营的 AI Agent 系统，支持输入主题/受众/平台/风格，
自动生成脚本、分镜、封面文案和发布策略。

## 技术栈
- 前端：Streamlit
- 后端：FastAPI + SQLAlchemy + MySQL
- Agent：LangChain + Coze/Dify
- 知识库：Chroma + text-embedding
- 大模型：DeepSeek API

## 快速启动
待补充...

## 团队
- PM：[名字]
- 前端：[名字]
- 后端：[名字]
- Agent：[名字]
- 数据/测试：[名字]
EOF

# 6. 提交初始结构
git add .
git commit -m "chore(init): 初始化项目结构和 README"
git push origin develop
```

### 1.2 编写需求分析文档草稿（40min）

在 `docs/requirements.md` 中完成以下内容：

```markdown
# 需求分析文档

## 1. 产品定位
面向短视频创作者、游戏策划、社交媒体运营的 AI 创作助手。
用户只需输入创作需求（主题、平台、受众、时长、风格），
系统自动生成多版本脚本、分镜表、封面文案和发布策略。

## 2. 目标用户画像

### 用户A：短视频博主（核心用户）
- 年龄 20-30 岁，日均创作 1-2 条短视频
- 痛点：脚本创作费时，不知道什么样的开头能留住观众
- 常用平台：抖音、小红书
- 期望：输入主题就能拿到可直接拍摄的脚本

### 用户B：游戏策划师
- 年龄 25-35 岁，需要为游戏宣传片或角色 PV 写脚本
- 痛点：需要分镜表和世界观设定，风格要求高
- 常用平台：B站、游戏社区
- 期望：输出包含分镜和角色对白的完整方案

### 用户C：品牌运营专员
- 年龄 22-32 岁，负责品牌社交媒体账号
- 痛点：需要同时管理多个平台，内容需要适配不同平台风格
- 常用平台：抖音 + 小红书 + 公众号
- 期望：同一主题生成多平台版本

## 3. 核心业务流程
[此处画流程图，见下方 1.3]

## 4. 功能范围
### 基本功能（必须）
- 用户注册、登录、退出
- 创作工作台（输入主题/受众/平台/时长/风格）
- 多 Agent 协作生成方案（热点分析 → 脚本创作 → 合规审查 → 发布策略）
- 3 个候选方案展示 + 推荐理由 + A/B 对比
- 历史记录查看
- 知识库检索（展示引用来源）
- 方案导出（Markdown）
- 样例数据统计看板

### 进阶功能（选做加分）
- 图片/视频素材输入 → 多模态创作
- 成员在线审核 + 版本回退
- 自动生成短视频样片（TTS + 图像生成 + FFmpeg）
```

### 1.3 画架构图与流程图（30min）

用 Draw.io / ProcessOn 画两组图，导出 PNG 放入 `docs/` 目录：

**图1：系统架构图**
```
┌─────────────────────────────────────────────────────┐
│                    前端 (Streamlit)                   │
│  登录/注册 │ 创作工作台 │ 方案浏览 │ 历史记录 │ 数据看板 │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (JWT)
┌──────────────────────▼──────────────────────────────┐
│                 后端 (FastAPI)                        │
│  Auth模块 │ 创作模块 │ 方案模块 │ 导出模块 │ 统计模块   │
└──────┬─────────────────────────────┬────────────────┘
       │                             │
┌──────▼──────┐              ┌──────▼──────┐
│   MySQL     │              │  Agent 层    │
│  数据库     │              │ LangChain   │
│             │              │ + Coze/Dify  │
└─────────────┘              └──────┬──────┘
                                    │
                          ┌─────────┼─────────┐
                    ┌─────▼────┐ ┌──▼───┐ ┌───▼────┐
                    │ 知识库    │ │ LLM  │ │ 工具层  │
                    │ Chroma   │ │DeepSeek│ │搜索/图片 │
                    └──────────┘ └──────┘ └────────┘
```

**图2：核心业务流程图**
```
用户登录 → 输入创作需求 → 系统异步处理
                                │
    ┌───────────────────────────┼───────────────────────────┐
    ▼                           ▼                           ▼
热点分析Agent              脚本创作Agent                合规审查Agent
(搜索热点话题)             (调用知识库+模板)            (敏感词+版权)
    │                           │                           │
    └───────────────────────────┼───────────────────────────┘
                                ▼
                         发布策略Agent
                    (A/B方案生成 + 评分排序)
                                │
                                ▼
                    返回 3 个候选方案 + 推荐
                                │
                                ▼
                    用户浏览 → 对比 → 导出
```

### 1.4 起草接口 JSON Schema（20min）

> 这是 Day 1 中午对齐时最重要的产出。P3 实现 API，P2 调 API，P4 对接 P3——三方都以此为准。

在 `docs/api_schema.md` 中写出核心接口的请求/响应格式：

```markdown
# API 接口约定（初版）

## 通用规范
- Base URL: `http://localhost:8000/api`
- 认证：Header `Authorization: Bearer <jwt_token>`
- 错误响应格式：`{"error": "错误类型", "detail": "详细说明"}`

## 1. POST /api/auth/register
Request:
{
  "username": "string",
  "password": "string",
  "email": "string (optional)"
}
Response 200:
{
  "id": 1,
  "username": "string",
  "message": "注册成功"
}

## 2. POST /api/auth/login
Request:
{
  "username": "string",
  "password": "string"
}
Response 200:
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}

## 3. POST /api/creation/start
Request:
{
  "topic": "秋季护肤好物推荐",
  "target_audience": "25-35岁职场女性",
  "platform": "douyin",           // douyin | xiaohongshu | bilibili
  "duration": "60s",              // 30s | 60s | 3min
  "style": "干货+轻娱乐"
}
Response 200:
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "创作任务已提交"
}

## 4. GET /api/task/{task_id}/status
Response 200 (进行中):
{
  "task_id": "uuid",
  "status": "processing",          // pending | processing | completed | failed
  "progress": "脚本创作Agent处理中...",
  "result": null
}
Response 200 (完成):
{
  "task_id": "uuid",
  "status": "completed",
  "progress": "完成",
  "result": {
    "session_id": 1,
    "schemes": [
      {
        "id": 1,
        "version": "A",
        "title": "...",
        "hook": "...",
        "scenes": [...],
        "hashtags": [...],
        "cover_text": "...",
        "score": 8.5,
        "rank": 1,
        "recommendation_reason": "..."
      },
      // B, C ...
    ],
    "best_version": "B"
  }
}

## 5. GET /api/schemes?session_id={id}
Response 200: { "schemes": [...] }

## 6. GET /api/scheme/{id}
Response 200: { "id": 1, "version": "A", ... }

## 7. GET /api/history?page=1&size=10
Response 200:
{
  "items": [
    {
      "session_id": 1,
      "topic": "...",
      "platform": "douyin",
      "created_at": "2024-...",
      "scheme_count": 3
    }
  ],
  "total": 5,
  "page": 1
}

## 8. GET /api/export/{scheme_id}?format=md
Response 200: (file download, Content-Type: text/markdown)

## 9. GET /api/knowledge/search?q=护肤&top_k=5
Response 200:
{
  "results": [
    {
      "id": 1,
      "title": "3个秋季护肤误区...",
      "content_snippet": "...",
      "platform": "douyin",
      "source": "抖音@某某创作者",
      "similarity": 0.92
    }
  ]
}

## 10. GET /api/stats/samples
Response 200:
{
  "topic_distribution": [{"name": "护肤", "count": 8}, {"name": "美食", "count": 6}, ...],
  "platform_distribution": [{"platform": "douyin", "count": 15}, ...],
  "monthly_trends": [{"month": "2024-07", "count": 5}, ...],
  "total_samples": 30
}
```

---

## 二、Day 1 上午 — 分发给各组员的启动任务

> 以下是你在组员群（或站会）里直接复制分发的任务清单。每人拿自己的部分，立刻开始。

---

### 📋 P2（前端开发）Day 1 任务

**目标：下午 6 点前 Streamlit 框架跑通，登录页能调通后端假数据。**

1. **环境搭建**
   ```bash
   git clone https://github.com/eeeedddduuuu/EngineeringTrainingGit
   cd EngineeringTrainingGit
   git checkout develop
   git checkout -b feature/frontend
   pip install streamlit requests
   ```

2. **创建前端目录结构**
   ```
   frontend/
   ├── app.py              # 主入口
   ├── pages/
   │   ├── login.py        # 登录/注册页
   │   ├── workspace.py    # 创作工作台
   │   ├── schemes.py      # 方案浏览
   │   ├── history.py      # 历史记录
   │   └── dashboard.py    # 数据看板
   └── utils/
       └── api.py          # API 调用封装
   ```

3. **今天必须完成：**
   - [ ] `app.py`：Streamlit 主入口，配置页面路由
   - [ ] `pages/login.py`：登录 + 注册表单界面（先不连后端也行，UI 要出来）
   - [ ] `utils/api.py`：封装 `api_post("/api/auth/login", data)` 和 `api_get(...)` 函数，配置 BASE_URL 和 JWT token 存储
   - [ ] 阅读 `docs/api_schema.md`，确认前端需要的数据格式是否清晰

4. **参考代码（`utils/api.py` 框架）：**
   ```python
   import streamlit as st
   import requests

   BASE_URL = "http://localhost:8000/api"

   def api_post(path, data):
       headers = {}
       if "token" in st.session_state:
           headers["Authorization"] = f"Bearer {st.session_state.token}"
       resp = requests.post(f"{BASE_URL}{path}", json=data, headers=headers)
       return resp.json()

   def api_get(path, params=None):
       headers = {}
       if "token" in st.session_state:
           headers["Authorization"] = f"Bearer {st.session_state.token}"
       resp = requests.get(f"{BASE_URL}{path}", params=params, headers=headers)
       return resp.json()
   ```

5. **第一天提交（Git）：**
   ```bash
   git add frontend/
   git commit -m "feat(frontend): 搭建 Streamlit 框架和登录页面"
   git push origin feature/frontend
   ```

---

### 📋 P3（后端开发）Day 1 任务

**目标：下午 6 点前数据库建表完成，FastAPI 框架跑通，注册/登录接口可用。**

1. **环境搭建**
   ```bash
   git clone https://github.com/eeeedddduuuu/EngineeringTrainingGit
   cd EngineeringTrainingGit
   git checkout develop
   git checkout -b feature/backend
   pip install fastapi uvicorn sqlalchemy sqlmodel pymysql passlib python-jose pydantic
   # 如果用 SQLite（推荐先不装 MySQL，省时间）：
   # 把 pymysql 换成 aiosqlite
   ```

2. **创建后端目录结构**
   ```
   backend/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py              # FastAPI 入口
   │   ├── config.py            # 配置（数据库连接、JWT密钥等）
   │   ├── database.py          # 数据库连接 + session
   │   ├── models/
   │   │   ├── __init__.py
   │   │   ├── user.py
   │   │   ├── session.py       # 创作会话
   │   │   ├── scheme.py        # 方案
   │   │   └── agent_log.py
   │   ├── schemas/
   │   │   ├── __init__.py
   │   │   ├── auth.py          # 注册/登录请求体
   │   │   └── creation.py      # 创作请求体
   │   ├── routers/
   │   │   ├── __init__.py
   │   │   ├── auth.py          # 注册/登录接口
   │   │   └── creation.py      # 创作相关接口
   │   └── utils/
   │       ├── __init__.py
   │       └── security.py      # JWT 生成/校验、密码哈希
   └── requirements.txt
   ```

3. **今天必须完成：**
   - [ ] `config.py`：数据库 URL、JWT_SECRET_KEY 等配置
   - [ ] `database.py`：SQLAlchemy engine + SessionLocal
   - [ ] `models/user.py`：User 模型（id, username, password_hash, email, created_at）
   - [ ] `utils/security.py`：`hash_password()`, `verify_password()`, `create_access_token()`, `decode_token()`
   - [ ] `routers/auth.py`：`POST /api/auth/register` + `POST /api/auth/login` → 返回真实 JWT
   - [ ] `main.py`：FastAPI app 创建 + CORS + 挂载 auth router
   - [ ] 用 Swagger UI (`http://localhost:8000/docs`) 自测注册和登录

4. **参照文档：**
   - 数据库表结构 → 看 `docs/requirements.md`（里面的核心表部分）
   - API 请求/响应格式 → 看 `docs/api_schema.md`
   - **严格按 Schema 的 JSON 格式来，P2 和 P4 都依赖这个**

5. **第一天提交：**
   ```bash
   git add backend/
   git commit -m "feat(backend): 完成数据库建模和注册登录 API"
   git push origin feature/backend
   ```

---

### 📋 P4（Agent 开发）Day 1 任务

**目标：下午 6 点前确定技术路线，跑通一次 LLM 调用，输出 Prompt 模板初版。**

1. **环境搭建**
   ```bash
   git clone https://github.com/eeeedddduuuu/EngineeringTrainingGit
   cd EngineeringTrainingGit
   git checkout develop
   git checkout -b feature/agent
   pip install langchain langchain-openai openai
   ```

2. **今天必做——技术验证：**
   - [ ] 在 DeepSeek 平台注册并获取 API Key
   - [ ] 写一个最简单的测试脚本 `backend/test_llm.py`：
     ```python
     from openai import OpenAI

     client = OpenAI(
         api_key="你的DeepSeek-API-Key",
         base_url="https://api.deepseek.com"
     )

     response = client.chat.completions.create(
         model="deepseek-chat",
         messages=[
             {"role": "system", "content": "你是短视频编剧。"},
             {"role": "user", "content": "写一条30秒抖音脚本，主题是秋季护肤。"}
         ]
     )
     print(response.choices[0].message.content)
     ```
   - [ ] 验证输出质量，截图保存
   - [ ] 决定技术路线：**纯 LangChain / Dify / 混合？（建议：核心编排用 LangChain，这样答辩时全是自己的代码）**

3. **今天必做——Prompt 模板初版：**
   在 `backend/prompts/` 下创建以下文件：
   - [ ] `prompts/trend_agent.yaml` — 热点分析 Agent 的 System Prompt
   - [ ] `prompts/script_agent.yaml` — 脚本创作 Agent 的 System Prompt
   - [ ] `prompts/review_agent.yaml` — 合规审查 Agent 的 System Prompt
   - [ ] `prompts/strategy_agent.yaml` — 发布策略 Agent 的 System Prompt

   每个 Prompt 文件格式示例（`prompts/script_agent.yaml`）：
   ```yaml
   name: 脚本创作Agent
   role: 资深短视频编剧，3年抖音/小红书/B站创作经验
   capability: 擅长将主题转化为可拍摄的脚本，精于开头钩子设计
   tools:
     - knowledge_search: 检索知识库获取同类爆款脚本参考
     - template_match: 根据平台和时长匹配脚本结构模板
   system_prompt: |
     你是{role}。
     你的任务是：根据用户提供的主题、受众、平台、时长和风格，
     生成3个不同版本的短视频脚本。

     每个脚本必须包含：
     1. 标题（吸引点击）
     2. 开头钩子（前3秒抓住注意力）
     3. 场景序列（每场景包含：序号、类型、时长、画面描述、口播文案）
     4. 推荐话题标签（3-5个）
     5. 封面文案

     调用工具 knowledge_search 获取同类爆款脚本作为参考。
     调用工具 template_match 获取对应平台的脚本结构模板。

     输出严格的 JSON 格式（不要加 markdown 代码块标记）。
   output_schema: |
     {
       "scripts": [
         {
           "version": "A",
           "title": "...",
           "hook": "...",
           "scenes": [{"seq": 1, "type": "...", "duration": "5s", "description": "...", "voiceover": "..."}],
           "hashtags": ["..."],
           "cover_text": "..."
         }
       ],
       "recommendation": {"best": "B", "reason": "..."}
     }
   ```

4. **第一天提交：**
   ```bash
   git add backend/prompts/ backend/test_llm.py
   git commit -m "feat(agent): 完成 LLM 调用验证和 Prompt 模板初版"
   git push origin feature/agent
   ```

---

### 📋 P5（数据/知识库 + 测试）Day 1 任务

**目标：下午 6 点前完成数据采集脚本框架，开始搜集样例数据。**

1. **环境搭建**
   ```bash
   git clone https://github.com/eeeedddduuuu/EngineeringTrainingGit
   cd EngineeringTrainingGit
   git checkout develop
   git checkout -b feature/data-kb
   pip install pandas requests beautifulsoup4 chromadb sentence-transformers
   ```

2. **今天必做——样例数据采集：**
   - [ ] 创建 `data/collect_samples.py`：采集脚本框架
   - [ ] 至少手动整理 15 条样例数据（目标 30 条，Day 1 完成一半），存为 `data/samples/samples.csv`，格式：
     ```csv
     title,tags,platform,publish_date,source,content_summary
     3个秋季护肤误区你中了几个？,护肤|干货|好物推荐,douyin,2024-09-15,抖音@某某创作者,前3秒指出常见护肤误区→逐一分析原因→推荐正确产品
     开学季宿舍好物分享,好物|学生党|性价比,xiaohongshu,2024-09-01,小红书@某某博主,以宿舍为场景→逐一展示好物→每件标注价格和购买渠道
     ```
     > 数据来源建议：直接去抖音/小红书/B站找一个你熟悉的领域的创作者，人工整理他们最近的热门视频信息。不用爬虫也行——纯人工整理的 30 条数据完全够用，而且来源可追溯。
   - [ ] 确保 3 个平台（抖音/小红书/B站）都有覆盖

3. **今天必做——知识库雏形：**
   - [ ] 创建 `data/build_kb.py`：
     ```python
     import chromadb
     from chromadb.utils import embedding_functions
     import pandas as pd

     # 1. 读取样例数据
     df = pd.read_csv("data/samples/samples.csv")

     # 2. 初始化 Chroma（本地模式）
     client = chromadb.PersistentClient(path="data/chroma_db")

     # 3. 使用 embedding 模型
     # 方案A：用 sentence-transformers 本地跑（免费）
     # 方案B：用 DeepSeek Embedding API（低费用）
     embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
         model_name="BAAI/bge-small-zh-v1.5"
     )

     # 4. 创建 collection 并写入
     collection = client.get_or_create_collection(
         name="media_knowledge",
         embedding_function=embedding_fn
     )

     for i, row in df.iterrows():
         collection.add(
             documents=[row["content_summary"]],
             metadatas=[{"title": row["title"], "platform": row["platform"], "tags": row["tags"], "source": row["source"]}],
             ids=[f"sample_{i}"]
         )

     print(f"知识库构建完成，共 {len(df)} 条")
     ```

4. **第一天提交：**
   ```bash
   git add data/
   git commit -m "feat(data): 完成样例数据采集框架和知识库雏形"
   git push origin feature/data-kb
   ```

---

## 三、Day 1 下午 2:00 — 全组站会议程（15min）

> PM 主持，所有组员参加。

1. **确认 Git 仓库**（2min）
   - 全员确认能 clone、能 push
   - 确认各自在正确的分支上工作

2. **接口 Schema 对齐**（5min）
   - PM 投屏 `docs/api_schema.md`
   - P2 确认：前端需要的数据格式够不够？
   - P3 确认：这些接口能不能实现？
   - P4 确认：Agent 输入输出的 JSON 格式有没有问题？
   - **有争议当场改，改完 PM 更新文档，全员以此为唯一真相来源**

3. **进度同步**（5min）
   - 每人 1 分钟：做了什么、遇到什么问题、下一步做什么
   - PM 记录到进度日志

4. **确认 Day 1 晚 DDL**（3min）
   - P3：数据库建表 + 注册登录 API 必须可用
   - P2：Streamlit 框架 + 登录页 UI
   - P4：LLM 调通 + Prompt 初版
   - P5：15 条样例数据 + 知识库能写入
   - PM：架构图 + 流程图完成 + API Schema 定稿

---

## 四、PM Day 1 下午工作清单

站会后 PM 自己做：

- [ ] 完善 `docs/requirements.md`（补全业务流程图嵌入）
- [ ] 完善 `docs/api_schema.md`（根据站会反馈修改）
- [ ] 检查各组员的 Git 提交情况（确认分支已 push）
- [ ] 写 Day 1 进度日志：
  ```markdown
  ## Day 1 进度日志

  ### 完成事项
  - Git 仓库初始化，创建 develop 分支和 feature 分支
  - 需求分析文档完成
  - 系统架构图和业务流程图完成
  - API 接口 Schema 定稿
  - P3：数据库建表 + 注册登录 API
  - P2：Streamlit 框架搭建
  - P4：DeepSeek API 调通 + Prompt 模板
  - P5：15 条样例数据采集 + Chroma 知识库雏形

  ### 问题与解决
  - （记录站会上提到的问题和解决方案）

  ### 明日计划
  - Day 2 上午：继续核心开发
  - Day 2 晚：首次联调（P2↔P3 打通）
  ```

---

## 五、Day 1 各角色核心 DDL 速查

| 角色 | 今日必须完成 | 检验方式 | 截止时间 |
|------|------------|---------|---------|
| P1 | 需求文档 + 架构图 + API Schema + Git 初始化 | `docs/` 目录文件齐全 | Day 1 晚 |
| P2 | Streamlit 框架跑通 + 登录页 UI | 本地 `streamlit run` 能出页面 | Day 1 晚 |
| P3 | 数据库建表 + `/api/auth/register` + `/api/auth/login` | Swagger UI 自测通过 | Day 1 晚 |
| P4 | DeepSeek API 调通 + 4 个 Agent 的 Prompt 模板 | `test_llm.py` 有输出 + prompts/ 有 4 个 yaml | Day 1 晚 |
| P5 | 15 条样例 CSV + Chroma 知识库能写入 | `data/samples/samples.csv` 有内容 | Day 1 晚 |

---

## 六、群发消息模板

> 直接把下面这段发到小组群：

```
@所有人 Day 1 任务已分配，请大家按自己的角色开始：

【Git 仓库】https://github.com/eeeedddduuuu/EngineeringTrainingGit

【操作步骤】
1. git clone 仓库后 checkout develop
2. 从 develop 创建你自己的 feature 分支：
   - 前端：feature/frontend
   - 后端：feature/backend
   - Agent：feature/agent
   - 数据/测试：feature/data-kb
3. 各自任务详见 PM 发的分工文档

【下午 2:00 站会】全员参加，对齐接口 Schema，15 分钟

【今晚 DDL】
- P3：注册登录 API 可用（最重要，P2 明天依赖你）
- P2：Streamlit 框架 + 登录页 UI
- P4：DeepSeek 调通 + Prompt 模板
- P5：15 条样例数据 + 知识库能写入
- PM：需求文档 + 架构图 + API Schema 定稿

【接口文档】docs/api_schema.md（开发时严格按这个格式来，有疑问下午站会提）
```
