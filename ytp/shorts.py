"""指定段落 → 9:16 直式 Shorts。"""
import subprocess
from pathlib import Path

from ytp.cut import output_dir


def cmd_shorts(video: Path, start: float, end: float, settings: dict) -> int:
    outdir = output_dir(video)
    out = outdir / "shorts.mp4"
    src = outdir / "clean.mp4"
    if not src.exists():
        src = video
    w, h = settings["shorts"]["width"], settings["shorts"]["height"]
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", str(start), "-to", str(end), "-i", str(src),
         "-vf", f"crop=ih*{w}/{h}:ih,scale={w}:{h}",
         "-c:v", "libx264", "-crf", str(settings["cut"]["crf"]),
         "-preset", settings["cut"]["preset"], "-c:a", "aac", str(out)],
        check=True)
    print(f"完成: {out}")
    return 0
