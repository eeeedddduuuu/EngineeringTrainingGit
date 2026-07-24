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

### P5（数据/测试）待完成
- [ ] 样例数据采集（目标30条，先完成15条）
- [ ] Chroma 知识库搭建脚本
- [ ] 创建 feature/data-kb 分支并首次提交

### 问题与风险
- 当前网络无法连接 GitHub（443端口被阻断），初始化在本地完成，网络恢复后推送

### 明日计划
- Day 2 上午：各角色继续开发
- Day 2 晚：首次联调（P2↔P3 注册登录流程打通）
