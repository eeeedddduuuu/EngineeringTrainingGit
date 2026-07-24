# API 接口约定

> **重要：** 这份文档是 P2（前端）、P3（后端）、P4（Agent）三方开发的唯一接口标准。任何修改必须先通知 PM 更新本文档。

---

## 通用规范

- **Base URL：** `http://localhost:8000/api`
- **Content-Type：** `application/json`（除文件上传外）
- **认证方式：** Header `Authorization: Bearer <jwt_token>`
- **所有业务接口**（除 `/api/auth/register` 和 `/api/auth/login`）均需携带有效 JWT Token
- **错误响应格式（统一）：**
  ```json
  {
    "error": "错误类型简码",
    "detail": "面向用户的中文错误说明"
  }
  ```

---

## 1. 用户认证模块

### 1.1 注册
```
POST /api/auth/register
```

**Request Body:**
```json
{
  "username": "string, 3-20位字母数字下划线",
  "password": "string, 6-50位",
  "email": "string (optional)"
}
```

**Response 200:**
```json
{
  "id": 1,
  "username": "zhangsan",
  "message": "注册成功"
}
```

**Response 400:**
```json
{
  "error": "user_exists",
  "detail": "用户名已被注册"
}
```

---

### 1.2 登录
```
POST /api/auth/login
```

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "username": "zhangsan"
}
```

**Response 401:**
```json
{
  "error": "invalid_credentials",
  "detail": "用户名或密码错误"
}
```

---

### 1.3 获取当前用户信息
```
GET /api/auth/me
```

**Request Header:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "id": 1,
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "created_at": "2026-07-24T10:00:00"
}
```

---

## 2. 创作模块

### 2.1 提交创作任务
```
POST /api/creation/start
```

**Request Header:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "topic": "秋季护肤好物推荐",
  "target_audience": "25-35岁职场女性",
  "platform": "douyin",
  "duration": "60s",
  "style": "干货+轻娱乐"
}
```

**字段说明：**
| 字段 | 类型 | 必填 | 可选值 |
|------|------|------|--------|
| topic | string | 是 | 任意文本 |
| target_audience | string | 是 | 任意文本 |
| platform | string | 是 | `douyin` / `xiaohongshu` / `bilibili` |
| duration | string | 是 | `30s` / `60s` / `3min` |
| style | string | 否 | 任意文本，默认"通用" |

**Response 202:**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "创作任务已提交，请轮询状态接口获取结果"
}
```

---

### 2.2 查询任务状态
```
GET /api/task/{task_id}/status
```

**Response 200 — 排队中:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "pending",
  "progress": "任务已排队，等待处理...",
  "result": null
}
```

**Response 200 — 处理中:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "processing",
  "progress": "脚本创作Agent正在生成方案B...",
  "result": null
}
```

**Response 200 — 完成:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "completed",
  "progress": "全部完成",
  "result": {
    "session_id": 42,
    "schemes": [
      {
        "id": 101,
        "version": "A",
        "title": "秋季护肤3步走，皮肤科医生都在用",
        "hook": "你还在用夏天的护肤品吗？99%的人秋天都踩了这个坑！",
        "scenes": [
          {
            "seq": 1,
            "type": "口播+画面",
            "duration": "5s",
            "description": "博主正面镜头，手持两瓶不同护肤品",
            "voiceover": "你还在用夏天的护肤品吗？99%的人秋天都踩了这个坑！"
          },
          {
            "seq": 2,
            "type": "画面切换",
            "duration": "8s",
            "description": "特写皮肤干燥画面→切换护肤步骤动画",
            "voiceover": "第一步：换掉你的洗面奶。夏季控油型会让秋天皮肤更干..."
          }
        ],
        "hashtags": ["#秋季护肤", "#护肤干货", "#好物推荐"],
        "cover_text": "秋季护肤3步走",
        "score": 8.5,
        "rank": 2
      },
      {
        "id": 102,
        "version": "B",
        "title": "...",
        "score": 9.2,
        "rank": 1
      },
      {
        "id": 103,
        "version": "C",
        "title": "...",
        "score": 7.8,
        "rank": 3
      }
    ],
    "recommendation": {
      "best_version": "B",
      "reason": "B方案开头钩子设置了悬念，前3秒留存率预估最高；结构紧凑适合60秒时长；话题标签覆盖热门搜索词。"
    }
  }
}
```

**Response 200 — 失败:**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "failed",
  "progress": null,
  "result": {
    "error": "agent_error",
    "detail": "脚本创作Agent调用超时，请重试"
  }
}
```

---

## 3. 方案浏览模块

### 3.1 获取某次会话的所有方案
```
GET /api/schemes?session_id=42
```

**Response 200:**
```json
{
  "session_id": 42,
  "topic": "秋季护肤好物推荐",
  "platform": "douyin",
  "created_at": "2026-07-24T14:30:00",
  "schemes": [
    {
      "id": 101,
      "version": "A",
      "title": "...",
      "hook": "...",
      "score": 8.5,
      "rank": 2
    }
  ]
}
```

---

### 3.2 获取单个方案详情
```
GET /api/scheme/101
```

**Response 200:**
```json
{
  "id": 101,
  "session_id": 42,
  "version": "A",
  "title": "秋季护肤3步走...",
  "hook": "你还在用夏天的护肤品吗？...",
  "scenes": [
    {"seq": 1, "type": "口播+画面", "duration": "5s", "description": "...", "voiceover": "..."}
  ],
  "hashtags": ["#秋季护肤", "#护肤干货"],
  "cover_text": "秋季护肤3步走",
  "score": 8.5,
  "rank": 2,
  "recommendation_reason": null
}
```

---

### 3.3 A/B 方案对比
```
POST /api/schemes/compare
```

**Request Body:**
```json
{
  "scheme_ids": [101, 102]
}
```

**Response 200:**
```json
{
  "schemes": [
    {
      "id": 101,
      "version": "A",
      "title": "...",
      "hook": "...",
      "scenes": [...],
      "score": 8.5
    },
    {
      "id": 102,
      "version": "B",
      "title": "...",
      "hook": "...",
      "scenes": [...],
      "score": 9.2
    }
  ],
  "diff_summary": "B方案在开头吸引力(+0.7)和结构紧凑度(+0.5)方面优于A方案"
}
```

---

## 4. 历史记录模块

### 4.1 获取历史会话列表
```
GET /api/history?page=1&size=10
```

**Response 200:**
```json
{
  "items": [
    {
      "session_id": 42,
      "topic": "秋季护肤好物推荐",
      "platform": "douyin",
      "status": "completed",
      "scheme_count": 3,
      "created_at": "2026-07-24T14:30:00"
    },
    {
      "session_id": 41,
      "topic": "开学季宿舍好物",
      "platform": "xiaohongshu",
      "status": "completed",
      "scheme_count": 3,
      "created_at": "2026-07-24T10:15:00"
    }
  ],
  "total": 15,
  "page": 1,
  "size": 10
}
```

---

## 5. 导出模块

### 5.1 导出方案为 Markdown
```
GET /api/export/101?format=md
```

**Response 200:** 文件下载
- **Content-Type:** `text/markdown; charset=utf-8`
- **Content-Disposition:** `attachment; filename="方案A_秋季护肤3步走.md"`

### 5.2 导出方案为 Word（进阶）
```
GET /api/export/101?format=docx
```

**Response 200:** 文件下载
- **Content-Type:** `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

---

## 6. 知识库检索模块

### 6.1 知识库检索
```
GET /api/knowledge/search?q=护肤&top_k=5
```

**Response 200:**
```json
{
  "query": "护肤",
  "results": [
    {
      "id": 1,
      "title": "3个秋季护肤误区，你中了几个？",
      "content_snippet": "前3秒指出常见误区 → 逐一分析 → 推荐产品...",
      "platform": "douyin",
      "tags": ["护肤", "干货", "好物推荐"],
      "source": "抖音 @某某创作者",
      "published_at": "2024-09-15",
      "similarity": 0.92
    },
    {
      "id": 5,
      "title": "...",
      "similarity": 0.87
    }
  ]
}
```

---

## 7. 统计看板模块

### 7.1 获取样例统计数据
```
GET /api/stats/samples
```

**Response 200:**
```json
{
  "total_samples": 30,
  "topic_distribution": [
    {"name": "护肤", "count": 8},
    {"name": "美食", "count": 6},
    {"name": "数码", "count": 5},
    {"name": "旅行", "count": 4},
    {"name": "穿搭", "count": 4},
    {"name": "其他", "count": 3}
  ],
  "platform_distribution": [
    {"platform": "douyin", "count": 12},
    {"platform": "xiaohongshu", "count": 10},
    {"platform": "bilibili", "count": 8}
  ],
  "monthly_trends": [
    {"month": "2024-07", "count": 5},
    {"month": "2024-08", "count": 7},
    {"month": "2024-09", "count": 10}
  ]
}
```

---

## 附录：状态码速查

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 202 | 已接受（异步任务已排队） |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 请求体校验失败（Pydantic 自动返回） |
| 500 | 服务器内部错误 |
