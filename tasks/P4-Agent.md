# P4 Agent/工作流开发 · 任务清单

**技术栈：** LangChain + DeepSeek API（建议）；Coze/Dify 辅助

---

## 文件结构

```
backend/
├── app/
│   └── agent/              ← 你需要新建这个目录
│       ├── __init__.py
│       ├── orchestrator.py ← Agent 编排主逻辑
│       ├── tools.py        ← 工具函数（知识库检索、搜索、敏感词过滤等）
│       └── scorer.py       ← 候选方案评分算法
└── prompts/               ← 4个Prompt模板（已写好，直接在此基础上改）
    ├── trend_agent.yaml
    ├── script_agent.yaml
    ├── review_agent.yaml
    └── strategy_agent.yaml
```

---

## Day 1 必须完成

- [ ] 注册 DeepSeek 并获取 API Key
- [ ] 写 `backend/test_llm.py` 跑通一次 DeepSeek API 调用，验证能正常返回
- [ ] 阅读 4 个 `prompts/*.yaml`，确认 Prompt 设计是否合理，有修改直接改
- [ ] 实现 `backend/app/agent/tools.py` 中第一个工具函数：`search_knowledge(query)`（调用 P5 的知识库检索接口 `/api/knowledge/search`）
- [ ] **提交 Git：** `feat(agent): LLM 调通、Prompt 确认、知识库检索工具`

## Day 2 必须完成

- [ ] 实现 `tools.py` 中剩余的 3 个工具函数：
  - `web_search(query)` — 搜索或抓取网页
  - `sensitive_word_filter(text)` — 敏感词检测
  - `template_match(platform, duration)` — 返回对应平台的脚本结构模板
- [ ] 实现 `scorer.py`：5 维度加权评分算法（钩子 25%、平台匹配 20%、受众匹配 20%、原创性 15%、可执行性 20%）
- [ ] 实现 `orchestrator.py`：流水线编排（趋势→脚本→审查→策略），每个节点调用 LLM + 对应工具
- [ ] 输出格式严格按 `docs/api_schema.md` 中 `task/{id}/status` 返回的 `result` 字段格式
- [ ] P3 能调用你的 orchestrator 并拿到完整 JSON
- [ ] **提交 Git：** `feat(agent): 完成4工具+评分算法+流水线编排`

## Day 3 必须完成

- [ ] Agent 调用日志写入数据库（每次调用记录 agent_name、input、output、tools_called、latency_ms、tokens_used、status）
- [ ] 与 P3 完成对接：后端创作接口触发 → Agent 异步执行 → 更新 task 状态
- [ ] 至少跑通 5 个成功案例（不同主题/平台/时长组合）
- [ ] 收集 3 个失败案例（用于测试报告）
- [ ] Prompt 调优：对比修改前后输出质量
- [ ] **提交 Git：** `feat(agent): 日志记录、成功/失败案例、Prompt 调优`

## Day 4 必须完成

- [ ] 配合 P5 的知识库检索联调
- [ ] 最终 Prompt 和配置导出
- [ ] 写 Agent 工作流设计说明文档（给 PM 放入报告）

---

## Agent 流水线（固定顺序，不可改）

```
用户输入 → 趋势分析Agent → 脚本创作Agent → 合规审查Agent → 发布策略Agent → 返回结果
               │               │               │               │
               ▼               ▼               ▼               ▼
           web_search    knowledge_search  sensitive_word  platform_template
                        template_match     _filter         scorer
```

## 工具清单（必须全部实现）

| 工具 | 函数名 | 输入 | 输出 |
|------|--------|------|------|
| 知识库检索 | `search_knowledge(query, top_k=3)` | str | list[{title, content, similarity}] |
| 网页搜索 | `web_search(query)` | str | list[{title, url, snippet}] |
| 敏感词过滤 | `sensitive_word_filter(text)` | str | {has_issue: bool, issues: list} |
| 模板匹配 | `template_match(platform, duration)` | str, str | {structure: list, tips: str} |

## 评分算法（5维度加权）

| 维度 | 权重 | 评分方式 |
|------|:----:|---------|
| 开头钩子吸引力 | 25% | LLM 打分 1-10 |
| 结构与平台匹配度 | 20% | 规则检查 + LLM 打分 |
| 目标受众匹配度 | 20% | LLM 打分 |
| 内容原创性 | 15% | 与知识库 top-3 结果的余弦相似度取反 |
| 可执行性 | 20% | 规则检查（场景数 ≤ 10，单场景 ≤ 30s） |

---

## 注意

- **输出 JSON 格式必须与 `docs/api_schema.md` 中 `/api/task/{id}/status` 的 result 字段完全一致**
- Prompt 文件放在 `backend/prompts/`，不要硬编码在代码里
- 所有 Agent 调用必须写日志到 agent_logs 表
- API Key 放在环境变量 `DEEPSEEK_API_KEY`，不要硬编码
