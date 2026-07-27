#!/usr/bin/env python3
"""doubao-multimodal — 豆包 2.0 Pro 多模态识别 + 本地 Whisper 音频转录

基于火山方舟 ARK API (doubao-seed-2-0-pro-260215)，支持 图片/视频/文件/音频 多模态输入。
音频通过本地 faster-whisper 转录后送模型分析（免费无限量）。
每日 200万 token 免费额度，支持 1-50 并发池。

用法:
    # === CLI ===
    python multimodal.py -i image.jpg -q "描述"
    python multimodal.py -v video.mp4 -q "分析"
    python multimodal.py -a audio.mp3
    python multimodal.py -f document.pdf -q "总结"
    python multimodal.py --history
    python multimodal.py --budget

    # === Python API ===
    from multimodal import call_multimodal, MultimodalPool
    result = call_multimodal(images=["img.jpg"], question="描述")
    pool = MultimodalPool(max_workers=10)
    pool.submit(images=["img.jpg"], task_id="t1")
    pool.wait_all()
"""
import sys
import os as _os
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    import ctypes as _ctypes
    def _get_unicode_argv():
        try:
            k = _ctypes.windll.kernel32
            k.GetCommandLineW.restype = _ctypes.c_wchar_p
            s = _ctypes.windll.shell32
            s.CommandLineToArgvW.argtypes = [_ctypes.c_wchar_p, _ctypes.POINTER(_ctypes.c_int)]
            s.CommandLineToArgvW.restype = _ctypes.POINTER(_ctypes.c_wchar_p)
            n = _ctypes.c_int()
            cmd = k.GetCommandLineW()
            if not cmd: return sys.argv
            raw = s.CommandLineToArgvW(cmd, _ctypes.byref(n))
            if not raw: return sys.argv
            try: r = [raw[i] for i in range(n.value)]
            finally: k.LocalFree(raw)
            return r if len(r) == len(sys.argv) else sys.argv
        except Exception: return sys.argv
    sys.argv = _get_unicode_argv()

import base64, json, argparse, time, hashlib, threading
import os
from pathlib import Path
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ── 配置 ──────────────────────────────────────────────────
def _get_api_key():
    # 三重 fallback：1)环境变量 → 2)app.config → 3)内置默认值（HTTP头必须ASCII）
    key = os.environ.get("ARK_API_KEY", "")
    if key and key.strip():
        return key.strip()
    try:
        from app.config import ARK_API_KEY as _cfg_key
        if _cfg_key and _cfg_key.strip():
            os.environ["ARK_API_KEY"] = _cfg_key
            return _cfg_key.strip()
    except ImportError:
        pass
    return "ark-342cf4b2-f72b-4267-a670-310451f37236-6372d"
API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL = "doubao-seed-2-0-pro-260215"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BUDGET_FILE = SCRIPT_DIR / ".multimodal_budget.json"
HISTORY_FILE = SCRIPT_DIR / ".multimodal_history.json"
_budget_lock = threading.Lock()

# 定价 (2.0 Pro: ¥1.0/4.0 per 1M tokens)
PRICING_IN = 1.0
PRICING_OUT = 4.0

# 每日免费额度（火山方舟 — 2.0 Pro 200万 token/天）
DAILY_FREE_QUOTA = {
    MODEL: 2_000_000,
}

# MIME 映射
IMAGE_MIMES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
}
VIDEO_MIMES = {
    ".mp4": "video/mp4", ".mkv": "video/x-matroska",
    ".avi": "video/avi", ".mov": "video/quicktime",
}
FILE_MIMES = {
    ".pdf": "application/pdf", ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown", ".csv": "text/csv",
    ".json": "application/json", ".xml": "application/xml",
}
AUDIO_MIMES = {
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac",
    ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".opus": "audio/ogg",
}

# ── Whisper 单例 ───────────────────────────────────────────
_whisper_model = None
_whisper_lock = threading.Lock()

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        with _whisper_lock:
            if _whisper_model is None:
                from faster_whisper import WhisperModel
                _whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
    return _whisper_model

# ── 预算管理 ──────────────────────────────────────────────
def _load_budget() -> dict:
    with _budget_lock:
        today = date.today().isoformat()
        if BUDGET_FILE.exists():
            b = json.loads(BUDGET_FILE.read_text("utf-8"))
            for key in ("daily", "free_remaining"):
                if key in b and isinstance(b[key], dict):
                    for d in list(b[key].keys()):
                        if d != today: del b[key][d]
            return b
        return {"total_cost": 0.0, "total_tokens": 0, "calls": 0,
                "daily": {}, "free_remaining": {}}

def _save_budget(b: dict):
    with _budget_lock:
        BUDGET_FILE.write_text(json.dumps(b, ensure_ascii=False, indent=2), "utf-8")

def _record_usage(prompt_tokens: int, completion_tokens: int) -> dict:
    b = _load_budget()
    total = prompt_tokens + completion_tokens
    cost = (prompt_tokens / 1_000_000) * PRICING_IN + (completion_tokens / 1_000_000) * PRICING_OUT

    today = date.today().isoformat()
    b.setdefault("free_remaining", {})
    daily_used = b["free_remaining"].setdefault(today, {}).get(f"daily_{MODEL}", 0)
    is_free = daily_used + total <= DAILY_FREE_QUOTA.get(MODEL, 0)
    if is_free:
        b["free_remaining"][today][f"daily_{MODEL}"] = daily_used + total
        cost = 0.0

    b["total_cost"] += cost
    b["total_tokens"] += total
    b["calls"] += 1
    d = b["daily"].setdefault(today, {"cost": 0.0, "tokens": 0, "calls": 0})
    d["cost"] += cost
    d["tokens"] += total
    d["calls"] += 1
    _save_budget(b)
    return {"cost": cost, "is_free": is_free, "budget": b}

# ── 历史记录 ──────────────────────────────────────────────
_history_lock = threading.Lock()

def _load_history() -> list:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text("utf-8"))
    return []

def _save_history(entry: dict):
    with _history_lock:
        records = _load_history()
        records.append(entry)
        HISTORY_FILE.write_text(json.dumps(records[-200:], ensure_ascii=False, indent=2), "utf-8")

# ── 编码工具 ──────────────────────────────────────────────
def _encode_file(filepath: str, mime_map: dict) -> tuple:
    path = Path(filepath)
    if not path.exists():
        return "", False, f"不存在: {filepath}"
    ext = path.suffix.lower()
    mime = mime_map.get(ext)
    if not mime:
        return "", False, f"不支持格式: {ext}"
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 100:
        return "", False, f"过大: {size_mb:.1f}MB"
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}", True, f"{path.name} ({size_mb:.1f}MB)"

def _transcribe_audio(filepath: str) -> str:
    """本地 Whisper 转录音频"""
    path = Path(filepath)
    try:
        model = _get_whisper()
        segments, info = model.transcribe(str(path), beam_size=5)
        # 自动检测语言
        language = info.language
        text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
        return f"[Whisper 转录 | {language} | {info.language_probability:.0%}置信]\n{text}"
    except Exception as e:
        return f"[转录失败: {e}]"

# ── 核心调用 ──────────────────────────────────────────────
def call_multimodal(
    images: list = None,
    videos: list = None,
    files: list = None,
    audios: list = None,
    question: str = "",
    max_tokens: int = 2048,
    timeout: int = 180,
) -> dict:
    """调用豆包 2.0 Pro 多模态分析。

    Args:
        images: 图片路径列表
        videos: 视频路径列表
        files: 文件路径列表
        audios: 音频路径列表（自动 Whisper 转录）
        question: 分析问题
        max_tokens: 最大输出 token
        timeout: 超时秒数
    """
    if not HAS_REQUESTS:
        return {"success": False, "error": "需要 pip install requests"}

    images = images or []
    videos = videos or []
    files = files or []
    audios = audios or []

    total_inputs = len(images) + len(videos) + len(files) + len(audios)
    if total_inputs == 0:
        return {"success": False, "error": "至少需要一个输入文件"}

    # 音频 → Whisper 转录
    audio_transcripts = []
    for a in audios:
        if Path(a).exists():
            transcript = _transcribe_audio(a)
            audio_transcripts.append(transcript)
            print(f"   🎵 {Path(a).name} → Whisper 转录 ({len(transcript)}字)", file=sys.stderr)

    # 自动问题
    if not question:
        parts = []
        if images: parts.append(f"{len(images)}张图片")
        if videos: parts.append(f"{len(videos)}段视频")
        if files: parts.append(f"{len(files)}个文件")
        if audios: parts.append(f"{len(audios)}段音频")
        question = f"请分析{'这些' if total_inputs > 1 else '这个'}{'、'.join(parts)}的内容。"

    # 整合音频转录到 prompt
    full_question = question
    if audio_transcripts:
        full_question += "\n\n以下是音频的转录文本：\n" + "\n\n".join(
            f"--- 音频{i+1} ---\n{t}" for i, t in enumerate(audio_transcripts)
        )

    # 构建消息
    content = [{"type": "text", "text": full_question}]
    for img in images:
        uri, ok, msg = _encode_file(img, IMAGE_MIMES)
        if ok: content.append({"type": "image_url", "image_url": {"url": uri}})
        else: print(f"   ⚠️ {msg}", file=sys.stderr)
    for vid in videos:
        uri, ok, msg = _encode_file(vid, VIDEO_MIMES)
        if ok: content.append({"type": "video_url", "video_url": {"url": uri}})
        else: print(f"   ⚠️ {msg}", file=sys.stderr)
    for f in files:
        uri, ok, msg = _encode_file(f, FILE_MIMES)
        if ok: content.append({"type": "file", "file": {"data": uri}})
        else: print(f"   ⚠️ {msg}", file=sys.stderr)

    # 动态 max_tokens
    base_tk = 2048
    if videos: base_tk = 4096
    if audios: base_tk = max(base_tk, 4096)
    max_tokens = min(base_tk * max(total_inputs, 1), 16384)

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    try:
        start = time.time()
        resp = requests.post(API_URL, json=payload,
                             headers={"Content-Type": "application/json",
                                      "Authorization": f"Bearer {_get_api_key()}"},
                             timeout=timeout,
                             proxies={"http": None, "https": None})
        elapsed = time.time() - start
        r = resp.json()
        if "choices" not in r:
            return {"success": False, "error": r.get("error", {}).get("message", str(r)[:300])}

        usage = r.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        budget_info = _record_usage(prompt_tokens, completion_tokens)

        result = {
            "success": True,
            "model": r.get("model", MODEL),
            "content": r["choices"][0]["message"]["content"],
            "usage": usage,
            "cost": budget_info["cost"],
            "is_free": budget_info["is_free"],
            "elapsed": elapsed,
            "inputs": {
                "images": len(images), "videos": len(videos),
                "files": len(files), "audios": len(audios),
            },
            "audio_transcripts": audio_transcripts,
        }
        _save_history({
            "time": datetime.now().isoformat()[:19],
            "question": question[:200],
            "content_preview": result["content"][:200],
            "tokens": total_tokens, "cost": budget_info["cost"],
            "inputs": result["inputs"],
        })
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── 并发池 ────────────────────────────────────────────────
class MultimodalPool:
    """多模态并发池 — 支持 1-50 并发"""

    def __init__(self, max_workers: int = 10, timeout: int = 300,
                 on_complete: callable = None, verbose: bool = True):
        self.max_workers = min(max(max_workers, 1), 50)
        self.timeout = timeout
        self.on_complete = on_complete
        self.verbose = verbose

        self._executor = None
        self._futures = {}
        self._results = {}
        self._lock = threading.Lock()
        self._submitted = 0
        self._completed = 0
        self._failed = 0

    def _ensure_executor(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def submit(self, images=None, videos=None, files=None, audios=None,
               question="", task_id=None, retries=1, on_complete=None) -> str:
        """提交一个多模态任务，返回 task_id"""
        self._ensure_executor()
        if task_id is None:
            self._submitted += 1
            task_id = str(self._submitted)

        task_info = {
            "task_id": task_id, "images": images, "videos": videos,
            "files": files, "audios": audios, "question": question,
            "retries": retries, "submitted_at": time.time(),
            "on_complete": on_complete,
        }
        future = self._executor.submit(self._run_task, task_info)
        with self._lock:
            self._futures[future] = task_info
        return task_id

    def _run_task(self, task_info: dict) -> dict:
        task_id = task_info["task_id"]
        retries = max(task_info.get("retries", 0), 0)
        last_error = None

        for attempt in range(retries + 1):
            result = call_multimodal(
                images=task_info.get("images"),
                videos=task_info.get("videos"),
                files=task_info.get("files"),
                audios=task_info.get("audios"),
                question=task_info.get("question", ""),
                timeout=self.timeout,
            )
            if result.get("success"):
                result["task_id"] = task_id
                result["elapsed"] = time.time() - task_info["submitted_at"]
                with self._lock:
                    self._results[task_id] = result
                    self._completed += 1
                if self.verbose:
                    tokens = result.get("usage", {}).get("total_tokens", 0)
                    free = " [FREE]" if result.get("is_free") else ""
                    inputs = result.get("inputs", {})
                    tags = []
                    if inputs.get("images"): tags.append(f"{inputs['images']}i")
                    if inputs.get("videos"): tags.append(f"{inputs['videos']}v")
                    if inputs.get("files"): tags.append(f"{inputs['files']}f")
                    if inputs.get("audios"): tags.append(f"{inputs['audios']}a")
                    print(f"[pool] {task_id} done {result['elapsed']:.0f}s {tokens}t{free} {' '.join(tags)}", flush=True)
                cb = task_info.get("on_complete") or self.on_complete
                if cb:
                    try: cb(result)
                    except Exception: pass
                return result
            last_error = result.get("error", "unknown")
            if attempt < retries:
                time.sleep((attempt + 1) * 10)

        fail_result = {"success": False, "error": last_error, "task_id": task_id,
                       "elapsed": time.time() - task_info["submitted_at"]}
        with self._lock:
            self._results[task_id] = fail_result
            self._failed += 1
        if self.verbose:
            print(f"[pool] {task_id} FAILED: {last_error[:80]}", flush=True)
        return fail_result

    def submit_and_wait(self, **kwargs) -> dict:
        tid = self.submit(**kwargs)
        self.wait_for(tid)
        return self.get_result(tid)

    def get_result(self, task_id: str) -> dict:
        with self._lock:
            return self._results.get(task_id)

    def wait_for(self, task_id: str, timeout=None):
        with self._lock:
            future = None
            for f, info in self._futures.items():
                if info["task_id"] == task_id:
                    future = f; break
        if future:
            try: future.result(timeout=timeout)
            except Exception: pass

    def wait_all(self, timeout=None) -> dict:
        if self._executor is None:
            return {"completed": 0, "failed": 0, "results": {}}
        for f in list(self._futures.keys()):
            try: f.result(timeout=timeout)
            except Exception: pass
        with self._lock:
            return {"completed": self._completed, "failed": self._failed,
                    "total": len(self._results), "results": dict(self._results)}

    def stats(self) -> dict:
        with self._lock:
            return {"submitted": self._submitted, "completed": self._completed,
                    "failed": self._failed, "pending": sum(1 for f in self._futures if not f.done())}

    def shutdown(self, wait=True):
        if self._executor:
            self._executor.shutdown(wait=wait, cancel_futures=not wait)
            self._executor = None

# ── CLI ───────────────────────────────────────────────────
def _show_budget():
    b = _load_budget()
    today = date.today().isoformat()
    d = b.get("daily", {}).get(today, {})
    free_used = b.get("free_remaining", {}).get(today, {}).get(f"daily_{MODEL}", 0)
    free_limit = DAILY_FREE_QUOTA.get(MODEL, 0)
    pct = free_used * 100 // free_limit if free_limit else 0

    print(f"💰 豆包 2.0 Pro 额度")
    print(f"   今日: {d.get('calls', 0)}次 | {d.get('tokens', 0):,} token | ¥{d.get('cost', 0):.4f}")
    if free_limit:
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"   免费: {bar} {free_used//1000}k / {free_limit//1000}k ({pct}%)")
    print(f"   累计: {b['calls']}次 | {b['total_tokens']:,} token | ¥{b['total_cost']:.4f}")

def main():
    parser = argparse.ArgumentParser(description="doubao-multimodal — 豆包 Pro + Whisper 多模态识别")
    parser.add_argument("-i", "--image", nargs="*", default=[], help="图片路径")
    parser.add_argument("-v", "--video", nargs="*", default=[], help="视频路径")
    parser.add_argument("-f", "--file", nargs="*", default=[], help="文件路径 (pdf/txt/...)")
    parser.add_argument("-a", "--audio", nargs="*", default=[], help="音频路径 (mp3/wav/... → Whisper转录)")
    parser.add_argument("-q", "--question", default="", help="自定义问题")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("-t", "--timeout", type=int, default=180)
    parser.add_argument("--history", action="store_true", help="历史记录")
    parser.add_argument("--budget", action="store_true", help="额度查看")
    parser.add_argument("--output", "-o", default="")

    args = parser.parse_args()

    if args.budget:
        _show_budget()
        return

    if args.history:
        records = _load_history()
        if not records:
            print("📭 暂无历史记录"); return
        print(f"📋 最近 {len(records)} 条记录:\n")
        for i, r in enumerate(reversed(records[-20:])):
            inp = r.get("inputs", {})
            tags = []
            if inp.get("images"): tags.append(f"{inp['images']}🖼️")
            if inp.get("videos"): tags.append(f"{inp['videos']}🎬")
            if inp.get("files"): tags.append(f"{inp['files']}📄")
            if inp.get("audios"): tags.append(f"{inp['audios']}🎵")
            print(f"  {i+1:2d}. [{r['time']}] {' '.join(tags)} | {r['tokens']}t ¥{r['cost']:.4f}")
            print(f"      Q: {r['question'][:80]}")
        return

    images = args.image or []
    videos = args.video or []
    files = args.file or []
    audios = args.audio or []

    if not any([images, videos, files, audios]):
        parser.print_help(); return

    tags = []
    if images: tags.append(f"{len(images)}🖼️")
    if videos: tags.append(f"{len(videos)}🎬")
    if files: tags.append(f"{len(files)}📄")
    if audios: tags.append(f"{len(audios)}🎵")
    print(f"🔍 豆包 2.0 Pro 多模态 | {' '.join(tags)}")
    if args.question:
        print(f"   ❓ {args.question[:100]}")

    result = call_multimodal(
        images=images, videos=videos, files=files, audios=audios,
        question=args.question, max_tokens=args.max_tokens, timeout=args.timeout,
    )

    if result["success"]:
        print(f"\n{'='*60}")
        print(result["content"])
        print(f"{'='*60}")
        usage = result.get("usage", {})
        free_tag = " [FREE]" if result.get("is_free") else ""
        print(f"\n📊 {result['model']}{free_tag} | "
              f"token: {usage.get('total_tokens', '?')} "
              f"(in:{usage.get('prompt_tokens', '?')}/out:{usage.get('completion_tokens', '?')}) | "
              f"耗时: {result['elapsed']:.1f}s | ¥{result['cost']:.6f}")
        if args.output:
            Path(args.output).write_text(result["content"], encoding="utf-8")
            print(f"💾 已保存: {args.output}")
    else:
        print(f"❌ {result['error']}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
