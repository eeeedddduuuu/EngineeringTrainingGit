#!/usr/bin/env python3
"""
vision-bridge-doubao — 豆包云端识图 Skill (分享版)

基于火山引擎 ARK API + doubao-seed-2-1-pro 视觉模型。
支持单图识别、多图对比、并发批量处理。

使用方法:
  1. 设置环境变量: set ARK_API_KEY=你的火山引擎API Key
  2. python vision_doubao.py image.jpg -q "描述这张图"
  3. 或作为 Python 模块导入使用

获取 API Key: https://console.volcengine.com/ark → 创建推理接入点 → API Key 管理
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    import ctypes
    def _get_unicode_argv():
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.GetCommandLineW.restype = ctypes.c_wchar_p
            shell32 = ctypes.windll.shell32
            shell32.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
            shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
            n = ctypes.c_int()
            cmd = kernel32.GetCommandLineW()
            if not cmd:
                return sys.argv
            raw_argv = shell32.CommandLineToArgvW(cmd, ctypes.byref(n))
            if not raw_argv:
                return sys.argv
            try:
                result = [raw_argv[i] for i in range(n.value)]
            finally:
                kernel32.LocalFree(raw_argv)
            if len(result) == len(sys.argv):
                return result
            return sys.argv
        except Exception:
            return sys.argv
    sys.argv = _get_unicode_argv()

import base64, json, os, argparse, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ── 配置 ──────────────────────────────────────────────────
# 从环境变量读取 API Key。启动前请设置:
#   Windows: set ARK_API_KEY=你的key
#   Linux/Mac: export ARK_API_KEY=你的key
ARK_KEY = os.environ.get("ARK_API_KEY", "")
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# 预算追踪文件（自动生成，记录使用量）
BUDGET_FILE = Path(__file__).resolve().parent / ".vision_budget.json"
_budget_lock = threading.Lock()

# 模型定价（元/百万 token，输入/输出）
PRICING = {
    "doubao-seed-2-0-mini-260428":  (0.15, 0.60),
    "doubao-seed-2-0-lite-260215":  (0.30, 1.20),
    "doubao-seed-2-0-pro-260215":   (1.00, 4.00),
    "doubao-seed-2-1-pro-260628":   (2.00, 8.00),
    "doubao-seed-2-1-turbo-260628": (0.80, 3.20),
}

# ── 模型选择 ──────────────────────────────────────────────
def auto_select_model(question: str, image_count: int) -> tuple:
    """根据任务复杂度自动选模型，返回 (model_id, reason)"""
    q = question.lower()
    is_simple = any(w in q for w in ["是什么", "有没有", "颜色", "简单", "几个"])
    is_complex = any(w in q for w in ["详细", "对比", "分析", "差异", "逐项",
                                       "画风", "比例", "结构", "装备", "风格"])
    is_compare = image_count >= 2
    q_len = len(question)

    if is_compare or is_complex or q_len > 100:
        return ("doubao-seed-2-0-lite-260215", "中等任务，用 lite")
    elif q_len < 30 or is_simple:
        return ("doubao-seed-2-0-mini-260428", "简单任务，用 mini")
    else:
        return ("doubao-seed-2-0-lite-260215", "默认，用 lite")


# ── 预算管理 ──────────────────────────────────────────────
def load_budget() -> dict:
    with _budget_lock:
        today = time.strftime("%Y-%m-%d")
        if BUDGET_FILE.exists():
            b = json.loads(BUDGET_FILE.read_text("utf-8"))
            for key in ("daily", "free_remaining"):
                if key in b and isinstance(b[key], dict):
                    for d in list(b[key].keys()):
                        if d != today:
                            del b[key][d]
            return b
        return {"total_cost": 0.0, "total_tokens": 0, "calls": 0,
                "daily": {}, "free_remaining": {}}

def save_budget(b: dict):
    with _budget_lock:
        BUDGET_FILE.write_text(json.dumps(b, ensure_ascii=False, indent=2), "utf-8")

def record_usage(model: str, usage: dict) -> dict:
    b = load_budget()
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", 0)
    input_price, output_price = PRICING.get(model, (0.30, 1.20))

    cost = (prompt_tokens / 1_000_000) * input_price + (completion_tokens / 1_000_000) * output_price

    today = time.strftime("%Y-%m-%d")
    if "free_remaining" not in b:
        b["free_remaining"] = {}

    b["total_cost"] += cost
    b["total_tokens"] += total
    b["calls"] += 1

    if today not in b["daily"]:
        b["daily"][today] = {"cost": 0.0, "tokens": 0, "calls": 0}
    b["daily"][today]["cost"] += cost
    b["daily"][today]["tokens"] += total
    b["daily"][today]["calls"] += 1

    save_budget(b)
    return {"cost": cost, "budget": b}


# ── 核心调用 ──────────────────────────────────────────────
def encode_image(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")
    ext = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}
    mime = mime_map.get(ext)
    if not mime:
        raise ValueError(f"不支持的格式: {ext}")
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def call_vision(image_paths: list, question: str = "", model: str = None,
                auto: bool = True, timeout: int = 120, max_tokens: int = None) -> dict:
    """调用豆包视觉模型识别图片。

    Args:
        image_paths: 图片路径列表
        question: 自定义问题（空则自动生成）
        model: 模型 ID 或别名 (mini/lite/pro/pro21/turbo21)
        auto: True=自动选模型, False=手动指定
        timeout: API 超时秒数
        max_tokens: 输出最大 token（None=自动: 2048×图片数, 上限 8192）

    Returns:
        {"success": True, "content": "...", "model": "...", "usage": {...}, ...}
    """
    if not HAS_REQUESTS:
        return {"success": False, "error": "需要 pip install requests"}

    if not ARK_KEY:
        return {"success": False, "error": "未设置 ARK_API_KEY 环境变量。请在启动前设置: set ARK_API_KEY=你的key"}

    if auto and not model:
        model, reason = auto_select_model(question, len(image_paths))
        print(f"[auto] {reason} | 模型: {model}", file=sys.stderr)

    if not question:
        n = len(image_paths)
        if n == 1:
            question = "请详细描述这张图片的内容，包括角色特征、色彩、构图、风格、细节。"
        else:
            question = f"请分别分析以下 {n} 张图片的内容，每张图片包括角色特征、色彩、构图、风格、细节。"

    content = [{"type": "text", "text": question}]
    for img in image_paths:
        content.append({"type": "image_url", "image_url": {"url": encode_image(img)}})

    if max_tokens is None:
        max_tokens = min(2048 * len(image_paths), 8192)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    try:
        resp = requests.post(ARK_URL, json=payload,
                             headers={"Content-Type": "application/json",
                                      "Authorization": f"Bearer {ARK_KEY}"},
                             timeout=timeout)
        r = resp.json()
        if "choices" not in r:
            return {"success": False, "error": r.get("error", {}).get("message", str(r)[:200])}

        usage = r.get("usage", {})
        budget_info = record_usage(model, usage)
        b = budget_info["budget"]
        today = time.strftime("%Y-%m-%d")

        return {
            "success": True,
            "model": r.get("model", model),
            "content": r["choices"][0]["message"]["content"],
            "usage": usage,
            "cost": budget_info["cost"],
            "today_cost": b["daily"].get(today, {}).get("cost", 0),
            "total_cost": b["total_cost"],
            "calls_today": b["daily"].get(today, {}).get("calls", 0),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── 并发池 ────────────────────────────────────────────────
class VisionPool:
    """豆包识图并发池 — 支持 1-50 并发，随时添加任务，互不影响"""

    def __init__(self, max_workers: int = 10, timeout: int = 300,
                 auto_model: bool = True, default_model: str = None,
                 on_complete: callable = None, verbose: bool = True):
        """
        Args:
            max_workers: 最大并发数 1-50
            timeout: 单次 API 请求超时秒数
            auto_model: 是否自动根据任务复杂度选模型
            default_model: 强制指定模型（auto_model=True 时忽略）
            on_complete: 每张图完成时的回调 fn(task_result) -> None
            verbose: 是否打印进度
        """
        self.max_workers = min(max(max_workers, 1), 50)
        self.timeout = timeout
        self.auto_model = auto_model
        self.default_model = default_model
        self.on_complete = on_complete
        self.verbose = verbose

        self._executor = None
        self._futures = {}
        self._results = {}
        self._lock = threading.Lock()
        self._total_submitted = 0
        self._total_completed = 0
        self._total_failed = 0
        self._active = False

    def _ensure_executor(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def submit(self, image_paths: list, question: str = "",
               task_id: str = None, retries: int = 1, on_complete: callable = None) -> str:
        """提交一个识图任务，返回 task_id。可随时调用，即时添加到队列。

        Args:
            image_paths: 图片路径列表（单图传 [path]，多图传 [path1, path2, ...]）
            question: 自定义问题（空则自动生成）
            task_id: 任务 ID（空则自动编号）
            retries: 失败重试次数
            on_complete: 完成回调 fn(task_result)

        Returns:
            task_id: 可用于 get_result() / wait_for()
        """
        return self._submit_internal(image_paths, question, task_id, retries, on_complete)

    def submit_batch(self, image_paths: list, question: str = "",
                     task_id: str = None, max_images: int = 10,
                     retries: int = 1, on_complete: callable = None) -> list:
        """提交多图批量识别任务。将多张关联图片一次性发给豆包 API 做对比分析。

        最大 10 张/次（超过自动拆分多批），适合：对比分析、批量归类、关联识别。

        Args:
            image_paths: 图片路径列表
            question: 自定义问题（空则自动生成多图 prompt）
            task_id: 任务 ID 前缀（自动加 _1, _2...）
            max_images: 每批最大图片数（上限 10，默认 10）
            retries: 每批失败重试次数
            on_complete: 完成回调 fn(task_result)

        Returns:
            list[task_id]: 所有子任务 ID 列表
        """
        max_images = min(max_images, 10)
        task_ids = []
        total = len(image_paths)

        for batch_idx in range(0, total, max_images):
            batch = image_paths[batch_idx:batch_idx + max_images]
            if len(batch) == 1 and batch_idx == 0 and total == 1:
                return [self._submit_internal(batch, question, task_id, retries, on_complete)]

            batch_num = batch_idx // max_images + 1
            total_batches = (total + max_images - 1) // max_images
            tid = f"{task_id}_b{batch_num}" if task_id else None

            if not question:
                question = (
                    f"请分别分析以下 {len(batch)} 张图片。对每张图片，"
                    f"描述角色特征、色彩、构图、风格、细节。"
                    f"如果图片之间有关联或差异，请指出。"
                )

            if self.verbose:
                print(f"[pool] submit_batch {batch_num}/{total_batches} ({len(batch)} images) "
                      f"tid={tid}", flush=True)

            tid = self._submit_internal(batch, question, tid, retries, on_complete)
            task_ids.append(tid)

        return task_ids

    def submit_all(self, image_groups: list, question: str = "",
                   task_id_prefix: str = None, max_images: int = 10,
                   retries: int = 1, on_complete: callable = None) -> list:
        """批量提交多组图片。每组独立一个 API 请求，组内图片相关联。

        Args:
            image_groups: 图片路径列表的列表
            question: 自定义问题
            task_id_prefix: 任务 ID 前缀
            max_images: 每组最大图片数（上限 10）
            retries: 失败重试次数
            on_complete: 完成回调

        Returns:
            list[task_id]: 所有子任务 ID 列表
        """
        all_task_ids = []
        for i, group in enumerate(image_groups):
            tid = f"{task_id_prefix}_g{i+1}" if task_id_prefix else None
            ids = self.submit_batch(group, question, tid, max_images, retries, on_complete)
            all_task_ids.extend(ids)
        return all_task_ids

    def _submit_internal(self, image_paths: list, question: str = "",
                         task_id: str = None, retries: int = 1,
                         on_complete: callable = None) -> str:
        self._ensure_executor()
        self._active = True

        if task_id is None:
            self._total_submitted += 1
            task_id = str(self._total_submitted)

        task_info = {
            "task_id": task_id,
            "image_paths": image_paths,
            "question": question,
            "retries": retries,
            "submitted_at": time.time(),
            "is_batch": len(image_paths) > 1,
            "on_complete": on_complete,
        }
        future = self._executor.submit(self._run_task, task_info)
        with self._lock:
            self._futures[future] = task_info
        return task_id

    def _run_task(self, task_info: dict) -> dict:
        task_id = task_info["task_id"]
        image_paths = task_info["image_paths"]
        question = task_info["question"]
        retries = max(task_info["retries"], 0)

        model = self.default_model
        reason = ""
        if self.auto_model and not model:
            model, reason = auto_select_model(question, len(image_paths))

        last_error = None
        for attempt in range(retries + 1):
            try:
                result = call_vision(
                    image_paths, question, model=model,
                    auto=False,
                    timeout=self.timeout,
                )
            except Exception as e:
                result = {"success": False, "error": str(e)}

            if result.get("success"):
                result["task_id"] = task_id
                result["image_paths"] = image_paths
                result["elapsed"] = time.time() - task_info["submitted_at"]
                result["model_used"] = model
                result["model_reason"] = reason

                with self._lock:
                    self._results[task_id] = result
                    self._total_completed += 1

                if self.verbose:
                    img_names = [Path(p).name for p in image_paths]
                    n = len(img_names)
                    batch_label = f"[batch:{n}]" if n > 1 else ""
                    tokens = result.get("usage", {}).get("total_tokens", 0)
                    print(f"[pool] {task_id} done {result['elapsed']:.0f}s {tokens}t "
                          f"{batch_label} {', '.join(img_names[:3])}"
                          f"{'...' if n > 3 else ''}", flush=True)

                task_cb = task_info.get("on_complete")
                if task_cb:
                    try:
                        task_cb(result)
                    except Exception:
                        pass
                elif self.on_complete:
                    try:
                        self.on_complete(result)
                    except Exception:
                        pass

                return result

            last_error = result.get("error", "unknown")
            if attempt < retries:
                wait = (attempt + 1) * 10
                if self.verbose:
                    print(f"[pool] {task_id} retry {attempt+1}/{retries} ({wait}s): {last_error[:60]}",
                          flush=True)
                time.sleep(wait)

        fail_result = {
            "success": False, "error": last_error, "task_id": task_id,
            "image_paths": image_paths,
            "elapsed": time.time() - task_info["submitted_at"],
        }
        with self._lock:
            self._results[task_id] = fail_result
            self._total_failed += 1

        if self.verbose:
            img_names = [Path(p).name for p in image_paths]
            print(f"[pool] {task_id} FAILED: {', '.join(img_names)} — {last_error[:80]}",
                  flush=True)

        if self.on_complete:
            try:
                self.on_complete(fail_result)
            except Exception:
                pass

        return fail_result

    def submit_and_wait(self, image_paths: list, question: str = "",
                        task_id: str = None, retries: int = 1) -> dict:
        """提交并阻塞等待这一个任务完成，返回结果"""
        tid = self.submit(image_paths, question, task_id, retries)
        self.wait_for(tid)
        return self.get_result(tid)

    def get_result(self, task_id: str) -> dict | None:
        with self._lock:
            return self._results.get(task_id)

    def wait_for(self, task_id: str, timeout: float = None):
        with self._lock:
            future = None
            for f, info in self._futures.items():
                if info["task_id"] == task_id:
                    future = f
                    break
        if future:
            try:
                future.result(timeout=timeout)
            except Exception:
                pass

    def wait_all(self, timeout: float = None) -> dict:
        """等待全部任务完成，返回统计"""
        if self._executor is None:
            return {"completed": 0, "failed": 0, "results": {}}

        for f in list(self._futures.keys()):
            try:
                f.result(timeout=timeout)
            except Exception:
                pass

        self._active = False
        with self._lock:
            return {
                "completed": self._total_completed,
                "failed": self._total_failed,
                "total": len(self._results),
                "results": dict(self._results),
            }

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for f in self._futures if not f.done())

    @property
    def completed_count(self) -> int:
        with self._lock:
            return self._total_completed

    @property
    def failed_count(self) -> int:
        with self._lock:
            return self._total_failed

    def stats(self) -> dict:
        with self._lock:
            return {
                "submitted": self._total_submitted,
                "completed": self._total_completed,
                "failed": self._total_failed,
                "pending": sum(1 for f in self._futures if not f.done()),
                "max_workers": self.max_workers,
            }

    def shutdown(self, wait: bool = True):
        if self._executor:
            self._executor.shutdown(wait=wait, cancel_futures=not wait)
            self._executor = None
            self._active = False


# ── CLI ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="vision-bridge-doubao — 豆包云端识图")
    parser.add_argument("images", nargs="*", help="图片路径")
    parser.add_argument("-q", "--question", default="", help="自定义提问")
    parser.add_argument("-c", "--compare", action="store_true", help="对比模式")
    parser.add_argument("-m", "--model", default="", help="模型别名: mini/lite/pro/pro21/turbo21")
    parser.add_argument("--no-auto", action="store_true", help="禁用自动选模型")
    parser.add_argument("--budget", action="store_true", help="查看预算报告")
    parser.add_argument("--list-models", action="store_true", help="列出模型")
    parser.add_argument("-t", "--timeout", type=int, default=120, help="超时秒数")

    args = parser.parse_args()

    if args.list_models:
        print("豆包视觉模型 — 价格 (输入/输出 元/百万token):\n")
        for mid, (in_p, out_p) in PRICING.items():
            print(f"  {mid}")
            print(f"    输入 ¥{in_p}  输出 ¥{out_p}")
            print()
        b = load_budget()
        print(f"累计: {b['calls']} 次调用, {b['total_tokens']} token, ¥{b['total_cost']:.4f}")
        return

    if args.budget:
        b = load_budget()
        today = time.strftime("%Y-%m-%d")
        today_data = b["daily"].get(today, {})
        print(f"今日: {today_data.get('calls', 0)} 次, {today_data.get('tokens', 0)} token, ¥{today_data.get('cost', 0):.4f}")
        print(f"累计: {b['calls']} 次, {b['total_tokens']} token, ¥{b['total_cost']:.4f}")
        return

    if not args.images:
        parser.print_help()
        return

    ALIASES = {"mini": "doubao-seed-2-0-mini-260428", "lite": "doubao-seed-2-0-lite-260215",
               "pro": "doubao-seed-2-0-pro-260215", "pro21": "doubao-seed-2-1-pro-260628",
               "turbo21": "doubao-seed-2-1-turbo-260628"}
    model = ALIASES.get(args.model, args.model) if args.model else ""

    question = args.question
    if args.compare and not question:
        question = "请对比这些图片：1.角色外观差异 2.画风差异 3.哪张更接近目标风格"

    result = call_vision(args.images, question, model, auto=not args.no_auto, timeout=args.timeout)

    if result["success"]:
        print("=" * 60)
        print(result["content"])
        print("=" * 60)
        usage = result.get("usage", {})
        print(f"{result['model']} | token: {usage.get('total_tokens', '?')} | "
              f"本次: ¥{result['cost']:.6f} | 今日: ¥{result['today_cost']:.4f} | "
              f"累计: ¥{result['total_cost']:.4f}")
    else:
        print(f"[ERROR] {result['error']}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
