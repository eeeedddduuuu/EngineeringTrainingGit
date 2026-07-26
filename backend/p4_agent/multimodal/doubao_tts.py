#!/usr/bin/env python3
"""doubao-tts — 豆包语音合成模型2.0 TTS 工具

通过火山引擎 openspeech API 将文本转为语音，支持音色选择、语速/音量/音调调节。

API 端点: POST https://openspeech.bytedance.com/api/v3/tts/create
模型: seed-audio-1.0 (中英) / seed-audio-1.0-multilingual (15+语言)

用法:
    # 交互式
    python doubao_tts.py

    # 命令行
    python doubao_tts.py generate -t "你好世界"
    python doubao_tts.py generate -t "你好世界" -s zh_female_qingxin --format mp3
    python doubao_tts.py generate -t "你好世界" --speed 10 --volume 5 --pitch -3
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
            if not cmd: return sys.argv
            raw_argv = shell32.CommandLineToArgvW(cmd, ctypes.byref(n))
            if not raw_argv: return sys.argv
            try: result = [raw_argv[i] for i in range(n.value)]
            finally: kernel32.LocalFree(raw_argv)
            return result if len(result) == len(sys.argv) else sys.argv
        except Exception: return sys.argv
    sys.argv = _get_unicode_argv()

import json, os, argparse, time, base64, uuid, hashlib
from pathlib import Path
from datetime import datetime, date
from urllib.request import Request, urlopen

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ── 配置 ──────────────────────────────────────────────────
API_KEY = os.environ.get("TTS_API_KEY", "769b27b4-b1f7-4eee-b44d-c67c1269c0b7")
API_BASE = "https://openspeech.bytedance.com/api/v3"
TTS_URL = f"{API_BASE}/tts/create"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
USAGE_FILE = SCRIPT_DIR / ".tts_usage.json"

# 模型
MODELS = {
    "multilingual": "seed-audio-1.0-multilingual",
    "1.0": "seed-audio-1.0",
}
DEFAULT_MODEL = "seed-audio-1.0-multilingual"

# 输出格式
FORMATS = ["mp3", "wav", "ogg_opus", "pcm"]
SAMPLE_RATES = [8000, 16000, 24000, 32000, 44100, 48000]

# 常见女声音色（用户可自行指定或试听 https://www.volcengine.com/docs/6561/1257544）
KNOWN_SPEAKERS = {
    "恬美女声": "zh_female_tianmei",
    "清新女声": "zh_female_qingxin",
    "知性女声": "zh_female_zhixing",
    "温柔女声": "zh_female_wenrou",
}


def _parse_args():
    parser = argparse.ArgumentParser(
        description="doubao-tts — 豆包语音合成模型2.0 TTS 工具")
    sub = parser.add_subparsers(dest="cmd")

    # generate
    p_gen = sub.add_parser("generate", aliases=["gen"], help="文本转语音")
    p_gen.add_argument("-t", "--text", required=True, help="待合成的文本（最大3000字符）")
    p_gen.add_argument("-m", "--model", default="multilingual", choices=list(MODELS.keys()),
                       help="模型版本 (默认: multilingual)")
    p_gen.add_argument("-s", "--speaker", default=None, help="音色ID，如 zh_female_qingxin")
    p_gen.add_argument("--format", "-f", default="mp3", choices=FORMATS, help="输出音频格式 (默认: mp3)")
    p_gen.add_argument("--sample-rate", "-r", type=int, default=24000, choices=SAMPLE_RATES,
                       help="采样率 (默认: 24000)")
    p_gen.add_argument("--speed", type=int, default=0, help="语速 [-50, 100]，默认0")
    p_gen.add_argument("--volume", type=int, default=0, help="音量 [-50, 100]，默认0")
    p_gen.add_argument("--pitch", type=int, default=0, help="音调 [-12, 12]，默认0")
    p_gen.add_argument("--subtitle", action="store_true", help="开启字幕（返回字级时间戳）")
    p_gen.add_argument("--watermark", action="store_true", help="添加显式水印")

    # stats
    sub.add_parser("stats", help="查看使用统计")

    # list
    sub.add_parser("list", aliases=["ls"], help="列出已生成音频")

    return parser.parse_args()


# ── 使用量追踪 ──────────────────────────────────────────
def _load_usage() -> dict:
    if USAGE_FILE.exists():
        return json.loads(USAGE_FILE.read_text("utf-8"))
    return {"daily": {}, "history": []}

def _save_usage(data: dict):
    USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

def _track(duration: float, text: str, model: str):
    today = date.today().isoformat()
    usage = _load_usage()
    daily = usage.setdefault("daily", {})
    day_data = daily.setdefault(today, {"count": 0, "duration": 0.0, "characters": 0})
    day_data["count"] += 1
    day_data["duration"] += duration
    day_data["characters"] += len(text)
    usage.setdefault("history", []).append({
        "time": datetime.now().isoformat()[:19],
        "text": text[:100],
        "duration": duration,
        "model": model,
    })
    _save_usage(usage)


# ── API 调用 ─────────────────────────────────────────────
def generate_tts(
    text: str,
    model: str = "seed-audio-1.0-multilingual",
    speaker: str = None,
    audio_format: str = "mp3",
    sample_rate: int = 24000,
    speed: int = 0,
    volume: int = 0,
    pitch: int = 0,
    enable_subtitle: bool = False,
    watermark: bool = False,
) -> dict:
    """
    调用豆包 TTS API 生成音频。

    Returns:
        dict: {"success": True/False, "audio_base64": ..., "duration": ..., "url": ..., "subtitle": ..., "error": ...}
    """
    payload = {
        "model": model,
        "text_prompt": text,
        "audio_config": {
            "format": audio_format,
            "sample_rate": sample_rate,
            "speech_rate": speed,
            "loudness_rate": volume,
            "pitch_rate": pitch,
            "enable_subtitle": enable_subtitle,
        },
    }

    if speaker:
        payload["speaker"] = speaker

    if watermark:
        payload["watermark"] = {"aigc_watermark": True}

    request_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": API_KEY,
        "X-Api-Request-Id": request_id,
    }

    try:
        if HAS_REQUESTS:
            resp = requests.post(TTS_URL, json=payload, headers=headers, timeout=120)
            data = resp.json()
        else:
            req = Request(TTS_URL, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": f"请求失败: {e}"}

    # API 成功时不返回 code 字段，直接返回 audio；失败时返回 code
    if "code" in data and data["code"] != 0:
        return {"success": False, "error": f"API 错误 {data.get('code')}: {data.get('message', '未知')}"}

    return {
        "success": True,
        "audio_base64": data.get("audio", ""),
        "duration": data.get("duration", 0),
        "original_duration": data.get("original_duration", 0),
        "url": data.get("url", ""),
        "subtitle": data.get("subtitle"),
    }


def _download_audio(url: str, text: str, fmt: str) -> Path:
    """从临时 URL 下载音频到本地"""
    short_hash = hashlib.md5((text + str(time.time())).encode()).hexdigest()[:6]
    safe_text = "".join(c for c in text[:40] if c.isalnum() or c in " _-").rstrip() or "tts"
    filename = f"{datetime.now().strftime('%Y-%m-%d')}_{safe_text}_{short_hash}.{fmt}"
    filepath = OUTPUT_DIR / filename

    try:
        if HAS_REQUESTS:
            r = requests.get(url, timeout=60)
            filepath.write_bytes(r.content)
        else:
            req = Request(url)
            with urlopen(req, timeout=60) as r:
                filepath.write_bytes(r.read())
    except Exception as e:
        print(f"⚠️ 下载失败: {e}", file=sys.stderr)
        return None

    return filepath


# ── 交互模式 ──────────────────────────────────────────────
def _ask(prompt: str, default="") -> str:
    val = input(prompt).strip()
    return val if val else default

def _ask_yn(prompt: str, default=True) -> bool:
    default_str = "Y/n" if default else "y/N"
    val = input(f"{prompt} [{default_str}]: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")

def interactive():
    """交互式 TTS 生成"""
    print("🎙️ 豆包 TTS 2.0 — 交互式语音合成\n")

    # 文本
    text = ""
    while not text:
        text = _ask("📝 输入文本 (max 3000字符): ")
        if not text:
            print("   请输入文本!", file=sys.stderr)
    if len(text) > 3000:
        print(f"   ⚠️ 文本长度 {len(text)}，超出3000字符将被截断", file=sys.stderr)

    # 模型
    print("\n📦 模型: 1) multilingual(多语言)  2) 1.0(中英)")
    m = _ask("  选择 [1]: ", "1")
    model = MODELS["multilingual"] if m in ("", "1") else MODELS["1.0"]

    # 音色
    print(f"\n🎤 音色 (留空使用默认，输入 ? 查看已知列表)")
    print(f"   已知: {' | '.join(KNOWN_SPEAKERS.keys())}")
    speaker = _ask("  音色ID或名称: ")
    if speaker in KNOWN_SPEAKERS:
        speaker = KNOWN_SPEAKERS[speaker]
    elif speaker == "?":
        speaker = ""

    # 格式
    print(f"\n🔊 输出格式: {' / '.join(FORMATS)}")
    fmt = _ask("  格式 [mp3]: ", "mp3")

    # 采样率
    print(f"📡 采样率: {' / '.join(str(r) for r in SAMPLE_RATES)}")
    sr = _ask("  采样率 [24000]: ", "24000")
    sample_rate = int(sr) if sr.isdigit() else 24000

    # 语速/音量/音调
    print("\n🎚️ 高级参数 (范围见提示，回车跳过)")
    speed = int(_ask("  语速 [-50~100, 默认0]: ", "0") or "0")
    volume = int(_ask("  音量 [-50~100, 默认0]: ", "0") or "0")
    pitch = int(_ask("  音调 [-12~12, 默认0]: ", "0") or "0")
    subtitle = _ask_yn("  开启字幕?", False)

    # 确认
    print(f"\n{'─'*50}")
    print(f"📝 文本: {text[:100]}{'...' if len(text)>100 else ''}")
    print(f"📦 模型: {model}")
    print(f"🎤 音色: {speaker or '默认'}")
    print(f"🔊 格式: {fmt} | 📡 {sample_rate}Hz")
    print(f"🎚️ 语速:{speed} 音量:{volume} 音调:{pitch} | 字幕:{'是' if subtitle else '否'}")
    if not _ask_yn("\n✅ 确认生成?"):
        print("已取消")
        return

    # 调用
    print("\n⏳ 合成中...")
    result = generate_tts(
        text=text, model=model, speaker=speaker,
        audio_format=fmt, sample_rate=sample_rate,
        speed=speed, volume=volume, pitch=pitch,
        enable_subtitle=subtitle,
    )

    if not result["success"]:
        print(f"❌ 失败: {result['error']}")
        return

    # 保存
    duration = result["duration"] or result["original_duration"] or 0
    filepath = None
    if result["audio_base64"]:
        short_hash = hashlib.md5((text + str(time.time())).encode()).hexdigest()[:6]
        safe_text = "".join(c for c in text[:30] if c.isalnum() or c in " _-").rstrip() or "tts"
        filename = f"{datetime.now().strftime('%Y-%m-%d')}_{safe_text}_{short_hash}.{fmt}"
        filepath = OUTPUT_DIR / filename
        audio_bytes = base64.b64decode(result["audio_base64"])
        filepath.write_bytes(audio_bytes)
        print(f"✅ 已保存: {filepath} ({len(audio_bytes)/1024:.1f} KB)")
    elif result["url"]:
        print("📥 下载中...")
        filepath = _download_audio(result["url"], text, fmt)
        if filepath:
            print(f"✅ 已保存: {filepath} ({filepath.stat().st_size/1024:.1f} KB)")

    print(f"⏱️ 时长: {duration:.1f}s | 计费时长: {result['original_duration']:.1f}s")

    if result.get("subtitle"):
        s = result["subtitle"]
        print(f"📜 字幕: {s.get('text', '')[:80]}")

    # 追踪
    _track(result["original_duration"] or duration, text, model)
    _show_usage()


def _show_usage():
    usage = _load_usage()
    today = date.today().isoformat()
    day = usage.get("daily", {}).get(today, {})
    if day:
        print(f"\n📊 今日: {day['count']}次 | {day['duration']:.1f}s | {day['characters']}字")
        print(f"   历史: {len(usage.get('history', []))}条")


# ── stats & list ──────────────────────────────────────────
def cmd_stats():
    usage = _load_usage()
    days = sorted(usage.get("daily", {}).items())
    if not days:
        print("📭 暂无使用记录")
        return
    print("📊 豆包 TTS 使用统计\n")
    total_count = total_dur = total_chars = 0
    for day, d in days:
        print(f"  {day}: {d['count']}次 | {d['duration']:.1f}s | {d['characters']}字")
        total_count += d['count']
        total_dur += d['duration']
        total_chars += d['characters']
    print(f"\n📈 累计: {total_count}次 | {total_dur:.1f}s ({total_dur/60:.1f}min) | {total_chars}字")


def cmd_list():
    usage = _load_usage()
    history = usage.get("history", [])
    if not history:
        print("📭 暂无生成记录")
        return
    print("📋 最近生成记录:\n")
    for i, h in enumerate(reversed(history[-20:])):
        print(f"  {i+1:2d}. [{h['time']}] {h['text'][:60]}  ⏱{h['duration']:.1f}s")


# ── main ──────────────────────────────────────────────────
def main():
    args = _parse_args()

    if args.cmd in ("generate", "gen"):
        model_name = MODELS.get(args.model, args.model)
        model = model_name if "/" not in args.model else args.model

        # 解析音色
        speaker = args.speaker
        if speaker and speaker in KNOWN_SPEAKERS:
            speaker = KNOWN_SPEAKERS[speaker]

        print(f"🎙️ 豆包 TTS | {model}")
        print(f"   📝 {args.text[:100]}{'...' if len(args.text)>100 else ''}")
        if speaker: print(f"   🎤 {speaker}")
        print(f"   🔊 {args.format} {args.sample_rate}Hz | 语速:{args.speed} 音量:{args.volume} 音调:{args.pitch}")
        if args.subtitle: print("   📜 字幕:开")
        if args.watermark: print("   🔒 水印:开")

        result = generate_tts(
            text=args.text, model=model, speaker=speaker,
            audio_format=args.format, sample_rate=args.sample_rate,
            speed=args.speed, volume=args.volume, pitch=args.pitch,
            enable_subtitle=args.subtitle, watermark=args.watermark,
        )

        if not result["success"]:
            print(f"❌ {result['error']}")
            sys.exit(1)

        duration = result["duration"] or result["original_duration"] or 0
        filepath = None

        if result["audio_base64"]:
            short_hash = hashlib.md5((args.text + str(time.time())).encode()).hexdigest()[:6]
            safe_text = "".join(c for c in args.text[:30] if c.isalnum() or c in " _-").rstrip() or "tts"
            filename = f"{datetime.now().strftime('%Y-%m-%d')}_{safe_text}_{short_hash}.{args.format}"
            filepath = OUTPUT_DIR / filename
            audio_bytes = base64.b64decode(result["audio_base64"])
            filepath.write_bytes(audio_bytes)
            print(f"✅ 已保存: {filepath} ({len(audio_bytes)/1024:.1f} KB)")
        elif result["url"]:
            filepath = _download_audio(result["url"], args.text, args.format)
            if filepath:
                print(f"✅ 已保存: {filepath} ({filepath.stat().st_size/1024:.1f} KB)")

        print(f"⏱️ 时长: {duration:.1f}s | 计费时长: {result['original_duration']:.1f}s")
        if result.get("subtitle"):
            s = result["subtitle"]
            print(f"📜 字幕: {s.get('text', '')[:100]}")

        _track(result["original_duration"] or duration, args.text, model)
        _show_usage()

    elif args.cmd == "stats":
        cmd_stats()
    elif args.cmd == "list" or args.cmd == "ls":
        cmd_list()
    else:
        interactive()


if __name__ == "__main__":
    main()
