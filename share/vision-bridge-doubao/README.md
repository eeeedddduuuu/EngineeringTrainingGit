# vision-bridge-doubao — 豆包云端识图（分享版）

基于火山引擎 ARK API + 豆包视觉模型的 Python 识图工具。

## 快速开始

### 1. 安装依赖
```bash
pip install requests
```

### 2. 设置 API Key
```bash
# Windows
set ARK_API_KEY=你的火山引擎API Key

# Linux/Mac
export ARK_API_KEY=你的火山引擎API Key
```

> 获取 Key：https://console.volcengine.com/ark → 创建推理接入点 → API Key 管理

### 3. 使用

**命令行：**
```bash
# 单图识别
python vision_doubao.py image.jpg -q "描述这张图"

# 多图对比
python vision_doubao.py img1.jpg img2.jpg -c

# 指定模型
python vision_doubao.py image.jpg -m pro21 -q "详细分析画风"

# 查看额度
python vision_doubao.py --budget

# 列出模型
python vision_doubao.py --list-models
```

**Python 代码：**
```python
from vision_doubao import call_vision

result = call_vision(["image.jpg"], "描述这张图")
if result["success"]:
    print(result["content"])
```

**并发批量：**
```python
from vision_doubao import VisionPool

pool = VisionPool(max_workers=10, verbose=True)

for img in ["a.jpg", "b.jpg", "c.jpg"]:
    pool.submit([img], "描述这张图", retries=3)

stats = pool.wait_all()
pool.shutdown()
```

## 可用模型

| 别名 | 模型 ID | 输入/输出（元/百万token） |
|------|------|------|
| `pro21` | doubao-seed-2-1-pro-260628 | ¥2.0 / ¥8.0 |
| `turbo21` | doubao-seed-2-1-turbo-260628 | ¥0.8 / ¥3.2 |
| `lite` | doubao-seed-2-0-lite-260215 | ¥0.3 / ¥1.2 |
| `mini` | doubao-seed-2-0-mini-260428 | ¥0.15 / ¥0.60 |

不指定模型时自动按任务复杂度选择（mini/lite）。

## API 参考

### call_vision(image_paths, question, model, auto, timeout, max_tokens)

| 参数 | 说明 |
|------|------|
| `image_paths` | 图片路径列表 |
| `question` | 自定义问题（空则自动生成） |
| `model` | 模型 ID 或别名 |
| `auto` | True=自动选模型 |
| `timeout` | 超时秒数，默认 120 |

返回：`{"success": True, "content": "...", "usage": {...}, "cost": ...}`

### VisionPool

| 方法 | 说明 |
|------|------|
| `submit(paths, question, task_id, retries)` | 提交单任务 |
| `submit_batch(paths, question, task_id, max_images, retries)` | 多图批量（≤10张/次，自动拆分） |
| `wait_all()` | 等待全部完成 |
| `get_result(task_id)` | 获取结果 |
| `stats()` | 查看进度 |
| `shutdown()` | 关闭池子 |

## 文件结构

```
share/vision-bridge-doubao/
├── vision_doubao.py   # 核心模块
└── README.md          # 本文档
```

## 注意事项

- 图片建议控制在 2MB 以下
- 多图对比时建议每批 2-4 张，质量最佳
- API Key 通过环境变量传入，代码中没有硬编码
- 使用量自动记录到 `.vision_budget.json`
