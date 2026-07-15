"""faster-whisper 轉錄 + SRT 輸出 + hotwords 替換 + 簡轉繁。"""
import json
from pathlib import Path

try:
    from opencc import OpenCC
    _cc = OpenCC("s2twp")
except Exception:  # ponytail: opencc 缺了就原樣輸出,不擋 pipeline
    _cc = None


def to_traditional(text: str) -> str:
    return _cc.convert(text) if _cc else text


def apply_replacements(text: str, replacements: dict) -> str:
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return text


def transcribe(media: Path, settings: dict, hotwords: list[str] | None = None) -> list[dict]:
    from faster_whisper import WhisperModel

    prompt = "。".join(hotwords) + "。" if hotwords else None
    try:
        model = WhisperModel(settings["model_size"], device="auto")
    except Exception:
        model = WhisperModel(settings["model_size"], device="cpu", compute_type="int8")
    try:
        segs, _ = model.transcribe(
            str(media), language=settings["language"],
            word_timestamps=True, initial_prompt=prompt,
        )
        segs = list(segs)
    except Exception:
        # GPU 半路失敗(缺 cuDNN 等)→ 退 CPU 重來
        model = WhisperModel(settings["model_size"], device="cpu", compute_type="int8")
        segs, _ = model.transcribe(
            str(media), language=settings["language"],
            word_timestamps=True, initial_prompt=prompt,
        )
        segs = list(segs)

    return [
        {
            "start": s.start,
            "end": s.end,
            "text": s.text.strip(),
            "words": [{"start": w.start, "end": w.end, "word": w.word} for w in (s.words or [])],
        }
        for s in segs
    ]


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments: list[dict], out: Path, replacements: dict | None = None):
    lines = []
    for i, seg in enumerate(segments, 1):
        text = to_traditional(apply_replacements(seg["text"], replacements or {}))
        lines.append(f"{i}\n{_ts(seg['start'])} --> {_ts(seg['end'])}\n{text}\n")
    out.write_text("\n".join(lines), encoding="utf-8")


def save_transcript(segments: list[dict], out: Path):
    out.write_text(json.dumps(segments, ensure_ascii=False, indent=1), encoding="utf-8")


def load_transcript(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))
