"""配置模块 — 加载 providers.json"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parent / "providers.json"


def load_config() -> dict[str, Any]:
    """加载完整的 providers.json 配置。"""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_provider_config(provider: str = "deepseek") -> dict[str, Any]:
    """获取指定 provider 的配置段（已扁平化，直接可用）。"""
    cfg = load_config()
    return cfg.get(provider, {})
