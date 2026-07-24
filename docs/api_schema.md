# API 接口规范（定稿·不可擅自修改）

> **本文件是 P2/P3/P4 三方开发的唯一接口标准。任何修改必须经 PM 同意并更新本文档。**

---

## 通用约束

| 项 | 值（定死） |
|---|-----------|
| Base URL | `http://localhost:8000/api` |
| Content-Type | `application/json` |
| 认证方式 | Header `Authorization: Bearer <token>` |
| Token 过期 | 24 小时 |
| 分页默认 | `page=1&size=10` |
| 错误格式 | `{"error": "错误码", "detail": "中文说明"}` |

**除 `/api/auth/register` 和 `/api/auth/login` 外，所有接口必须携带有效 Token。**

---

## 1. 用户认证（P3 必做 · P2 对接）

### `POST /api/auth/register`

```
请求:
{
  "username": "string, 3-20位, 仅允许 a-z A-Z 0-9 _",
  "password": "string, 6-50位",
  "email": "string | null"
}

成功 200:
{
  "id": 1,
  "username": "zhangsan",
  "message": "注册成功"
}

失败:
400  {"error": "user_exists",       "detail": "用户名已被注册"}
422  Pydantic 自动校验错误
```

### `POST /api/auth/login`

```
请求:
{
  "username": "string",
  "password": "string"
}

成功 200:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "username": "zhangsan"
}

失败:
401  {"error": "invalid_credentials", "detail": "用户名或密码错误"}
```

### `GET /api/auth/me`

```
Header: Authorization: Bearer <token>

成功 200:
{
  "id": 1,
  "username": "zhangsan",
  "email": null,
  "created_at": "2026-07-24T10:00:00"
}

失败:
401  Token 无效或过期
404  用户不存在
```

---

## 2. 创作流程（P3 核心 · P2/P4 对接）

### `POST /api/creation/start`

```
Header: Authorization: Bearer <token>

请求:
{
  "topic":           "string, 必填, 1-255字",
  "target_audience": "string, 必填, 1-100字",
  "platform":        "douyin | xiaohongshu | bilibili",
  "duration":        "30s | 60s | 3min",
  "style":           "string, 选填, 默认'通用', 最长100字"
}

成功 202:
{
  "task_id": "uuid",
  "status": "pending",
  "message": "创作任务已提交"
}

失败:
400  参数校验不通过
401  未登录
```

### `GET /api/task/{task_id}/status`

```
Header: Authorization: Bearer <token>

成功 200（排队中）:
{
  "task_id": "uuid",
  "status": "pending",
  "progress": "任务已排队",
  "result": null
}

成功 200（处理中）:
{
  "task_id": "uuid",
  "status": "processing",
  "progress": "当前步骤描述, 如: 脚本创作Agent处理中...",
  "result": null
}

成功 200（完成）:
{
  "task_id": "uuid",
  "status": "completed",
  "progress": "全部完成",
  "result": {
    "session_id": 42,
    "schemes": [
      {
        "id": 101,
        "version": "A",
        "title": "string",
        "hook": "string",
        "scenes": [
          {
            "seq": 1,
            "type": "口播 | 画面切换 | 特写 | 转场",
            "duration": "5s",
            "description": "string",
            "voiceover": "string"
          }
        ],
        "hashtags": ["#tag1", "#tag2"],
        "cover_text": "string",
        "score": 8.5,
        "rank": 2
      }
    ],
    "recommendation": {
      "best_version": "B",
      "reason": "string"
    }
  }
}

成功 200（失败）:
{
  "task_id": "uuid",
  "status": "failed",
  "progress": null,
  "result": {
    "error": "agent_error | timeout | unknown",
    "detail": "string"
  }
}

失败:
401  未登录
404  task_id 不存在
```

---

## 3. 方案浏览（P2/P3）

### `GET /api/schemes?session_id={id}`

```
Header: Authorization: Bearer <token>

成功 200:
{
  "session_id": 42,
  "topic": "string",
  "platform": "douyin",
  "created_at": "2026-07-24T14:30:00",
  "schemes": [
    {
      "id": 101,
      "version": "A",
      "title": "string",
      "hook": "string",
      "score": 8.5,
      "rank": 2
    }
  ]
}

失败:
401  未登录
404  session_id 不存在
```

### `GET /api/scheme/{id}`

```
Header: Authorization: Bearer <token>

成功 200:
{
  "id": 101,
  "session_id": 42,
  "version": "A",
  "title": "string",
  "hook": "string",
  "scenes": [{"seq":1, "type":"...", "duration":"...", "description":"...", "voiceover":"..."}],
  "hashtags": ["..."],
  "cover_text": "string",
  "score": 8.5,
  "rank": 2
}

失败:
401  未登录
404  方案不存在
```

### `POST /api/schemes/compare`

```
Header: Authorization: Bearer <token>

请求:
{
  "scheme_ids": [101, 102]
}

成功 200:
{
  "schemes": [ {完整方案对象}, {完整方案对象} ],
  "diff_summary": "B方案在开头吸引力(+0.7)和结构紧凑度(+0.5)方面优于A方案"
}

失败:
400  scheme_ids 数量不在 2-3 个之间
401  未登录
```

---

## 4. 历史记录（P2/P3）

### `GET /api/history?page=1&size=10`

```
Header: Authorization: Bearer <token>

成功 200:
{
  "items": [
    {
      "session_id": 42,
      "topic": "string",
      "platform": "douyin",
      "status": "completed",
      "scheme_count": 3,
      "created_at": "2026-07-24T14:30:00"
    }
  ],
  "total": 15,
  "page": 1,
  "size": 10
}
```

---

## 5. 导出（P3 · P2 调用）

### `GET /api/export/{scheme_id}?format=md`

```
Header: Authorization: Bearer <token>

成功 200:  文件下载 Content-Type: text/markdown
失败 400:  不支持的 format
失败 404:  scheme_id 不存在
```

---

## 6. 知识库检索（P5 提供 · P4 调用）

### `GET /api/knowledge/search?q={关键词}&top_k=5`

```
Header: Authorization: Bearer <token>

成功 200:
{
  "query": "护肤",
  "results": [
    {
      "id": 1,
      "title": "string",
      "content_snippet": "string (前200字)",
      "platform": "douyin | xiaohongshu | bilibili",
      "tags": ["tag1", "tag2"],
      "source": "string",
      "similarity": 0.92
    }
  ]
}

失败:
400  q 参数为空
```

---

## 7. 统计看板（P5 提供 · P2 展示）

### `GET /api/stats/samples`

```
Header: Authorization: Bearer <token>

成功 200:
{
  "total_samples": 30,
  "topic_distribution":  [{"name": "护肤", "count": 8}, ...],
  "platform_distribution": [{"platform": "douyin", "count": 12}, ...],
  "monthly_trends": [{"month": "2024-07", "count": 5}, ...]
}
```

---

## 附录

### 错误码速查

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 202 | 异步任务已接受 |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 404 | 资源不存在 |
| 422 | Pydantic 校验失败（自动） |
| 500 | 服务器内部错误 |

### 字段枚举值（定死的）

| 字段 | 允许的值 |
|------|---------|
| platform | `douyin` `xiaohongshu` `bilibili` |
| duration | `30s` `60s` `3min` |
| task status | `pending` `processing` `completed` `failed` |
| scene type | `口播` `画面切换` `特写` `转场` |
