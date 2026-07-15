"""設定載入:repo 內建預設值 + ~/.config/rushcut/ 使用者覆寫。"""
import json
import os
import shutil
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

DEFAULTS = {
    "model_size": "large-v3",
    "language": "zh",
    "silence": {"noise_db": -30, "min_silence_sec": 0.45, "keep_silence_sec": 0.3},
    "cut": {"min_keep_sec": 0.2, "crf": 18, "preset": "veryfast"},
    "shorts": {"width": 1080, "height": 1920},
}


def config_dir() -> Path:
    return Path(os.environ.get("RUSHCUT_CONFIG", Path.home() / ".config" / "rushcut"))


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings() -> dict:
    f = config_dir() / "settings.json"
    if f.exists():
        return _deep_merge(DEFAULTS, json.loads(f.read_text()))
    return dict(DEFAULTS)


def load_hotwords() -> dict:
    f = config_dir() / "hotwords.json"
    if f.exists():
        data = json.loads(f.read_text())
        return {"hotwords": data.get("hotwords", []), "replacements": data.get("replacements", {})}
    return {"hotwords": [], "replacements": {}}


def load_channel() -> str:
    f = config_dir() / "channel.md"
    return f.read_text() if f.exists() else ""


def cmd_init() -> int:
    dst = config_dir()
    dst.mkdir(parents=True, exist_ok=True)
    for tpl in TEMPLATES.iterdir():
        target = dst / tpl.name
        if target.exists():
            print(f"skip(已存在): {target}")
        else:
            shutil.copy(tpl, target)
            print(f"建立: {target}")
    return 0
