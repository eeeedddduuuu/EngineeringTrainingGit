# 项目进度日志

---

## Day 1（2026-07-24）

### PM 完成
- [x] Git 仓库初始化（https://github.com/eeeedddduuuu/EngineeringTrainingGit）
- [x] 项目目录结构创建（frontend/ backend/ data/ docs/ tests/）
- [x] .gitignore、README.md 编写
- [x] 需求分析文档（docs/requirements.md）
- [x] API 接口 Schema 定稿（docs/api_schema.md）
- [x] 系统架构图与业务流程图
- [x] 后端框架代码（FastAPI + SQLAlchemy + JWT）
- [x] 数据库模型定义（User, Session, Scheme, AgentLog, KnowledgeItem）
- [x] 注册/登录 API 实现
- [x] 前端框架搭建（Streamlit + 登录页 + 创作工作台）
- [x] 4 个 Agent 的 Prompt 模板（trend/script/review/strategy）
- [x] 任务分发文档（题目3-PM初步计划与任务分发.md）

### P2（前端）待完成
- [ ] Streamlit 框架拉取并本地跑通
- [ ] 完善登录页与后端联调
- [ ] 创建 feature/frontend 分支并首次提交

### P3（后端）待完成
- [ ] 拉取代码，确认数据库建模
- [ ] 完善认证中间件（OAuth2PasswordBearer）
- [ ] 创建 feature/backend 分支并首次提交

### P4（Agent）待完成
- [ ] DeepSeek API Key 申请
- [ ] test_llm.py 编写并验证调用
- [ ] 基于 Prompt 模板实现第一个 Agent 调用链路
- [ ] 创建 feature/agent 分支并首次提交

### P5（数据/测试）完成
- [x] 样例数据确认（samples.xlsx，50条，4类别，3平台，跨2年）
- [x] Chroma 知识库搭建（bge-small-zh-v1.5 + 语义检索验证通过）
- [x] `/api/knowledge/search` 接口实现（Top-K 语义检索，含相似度分数）
- [x] `/api/stats/samples` 接口实现（主题分布/平台分布/月度趋势）
- [x] 统计图表生成（4张：topic/pie, platform/bar, monthly/line, tag/barh）
- [x] pytest 测试用例编写（14条：auth 8条 + knowledge 6条 + stats 5条）
- [x] Python 3.9 兼容性修复（Optional语法 + bcrypt 5.x 兼容）
- [x] 后端 Bug 修复（auth.py 函数顺序 + main.py 启动建表）
- [x] 创建 feature/data-kb 分支并提交（51 files, 3037 lines）
- [ ] GitHub 推送（需 repo owner 添加 HH613P 为 collaborator）

### ⚠️ 需 P1 协调
- GitHub 仓库 `eeeedddduuuu/EngineeringTrainingGit` 需将 `HH613P` 添加为 collaborator 后才能推送

### 问题与风险
- 当前网络无法连接 GitHub（443端口被阻断），初始化在本地完成，网络恢复后推送
- HuggingFace 需通过镜像 `hf-mirror.com` 下载 Embedding 模型

### 明日计划
- Day 2 上午：各角色继续开发
- Day 2 晚：首次联调（P2↔P3 注册登录流程打通）
