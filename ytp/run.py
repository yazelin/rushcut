"""全 pipeline orchestration:資料夾內每支影片 cut → srt → pack(冪等)。"""
from pathlib import Path

from ytp.cut import cmd_cut, cmd_srt
from ytp.pack import cmd_pack

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}


def cmd_run(folder: Path, settings: dict, force: bool = False, auto_judge: bool = True) -> int:
    videos = sorted(p for p in folder.iterdir()
                    if p.suffix.lower() in VIDEO_EXTS and "output" not in p.parts)
    if not videos:
        print(f"{folder} 沒有影片")
        return 1
    for v in videos:
        print(f"== {v.name} ==")
        cmd_cut(v, settings, auto_judge=auto_judge, force=force)
        cmd_srt(v, settings, force=force)
        cmd_pack(v, settings, force=force)
        print(f"提示:封面與 Shorts 是操作員步驟——讀 output/{v.stem}/titles.md 選標題後,"
              f"照 cover-style.md 生 cover.png;精華段用 `ytp shorts` 轉直式")
    return 0
