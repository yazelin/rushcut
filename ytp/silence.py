"""靜音偵測:ffmpeg silencedetect → drop 區間。"""
import re
import subprocess
from pathlib import Path


def media_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def parse_silencedetect(stderr: str) -> list[tuple[float, float]]:
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", stderr)]
    # 片尾靜音沒有 silence_end,配對到的才算;結尾的交給 to_drops 用 duration 收
    pairs = list(zip(starts, ends))
    if len(starts) == len(ends) + 1:
        pairs.append((starts[-1], float("inf")))
    return pairs


def detect_silences(video: Path, noise_db: float, min_silence_sec: float) -> list[tuple[float, float]]:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_sec}",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return parse_silencedetect(proc.stderr)


def silences_to_drops(silences, keep_silence_sec: float, duration: float) -> list[tuple[float, float]]:
    """每段靜音頭尾各保留 keep_silence_sec 的呼吸感,其餘剪掉。"""
    drops = []
    for start, end in silences:
        end = min(end, duration)
        # 片頭/片尾的靜音整段剪(只留一側 keep)
        s = start + (keep_silence_sec if start > 0 else 0)
        e = end - (keep_silence_sec if end < duration else 0)
        if e - s > 0:
            drops.append((s, e))
    return drops
