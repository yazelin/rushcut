"""順剪執行:drop 區間合併 → ffmpeg trim/concat → 淨毛片 + 剪輯對照表。"""
import shutil
import subprocess
from pathlib import Path

from ytp import config
from ytp.silence import detect_silences, media_duration, silences_to_drops
from ytp.transcribe import save_transcript, transcribe, write_srt


def output_dir(video: Path) -> Path:
    d = video.parent / "output" / video.stem
    d.mkdir(parents=True, exist_ok=True)
    return d


def merge_drops(drops: list[tuple[float, float]], duration: float, min_keep_sec: float) -> list[tuple[float, float]]:
    """重疊/相鄰 drop 合併,取補集為 keep;太短的 keep 併回丟棄。"""
    if not drops:
        return [(0.0, duration)]
    drops = sorted((max(0.0, s), min(duration, e)) for s, e in drops if e > s)
    merged = [list(drops[0])]
    for s, e in drops[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    keeps, pos = [], 0.0
    for s, e in merged:
        if s - pos >= min_keep_sec:
            keeps.append((pos, s))
        pos = e
    if duration - pos >= min_keep_sec:
        keeps.append((pos, duration))
    return keeps


def execute_cut(video: Path, keeps: list[tuple[float, float]], out: Path, settings: dict):
    parts_v, parts_a, filters = [], [], []
    for i, (s, e) in enumerate(keeps):
        filters.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}];")
        filters.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}];")
        parts_v.append(f"[v{i}]")
        parts_a.append(f"[a{i}]")
    n = len(keeps)
    fc = "".join(filters) + "".join(
        v + a for v, a in zip(parts_v, parts_a)
    ) + f"concat=n={n}:v=1:a=1[outv][outa]"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
         "-filter_complex", fc, "-map", "[outv]", "-map", "[outa]",
         "-c:v", "libx264", "-crf", str(settings["cut"]["crf"]),
         "-preset", settings["cut"]["preset"], "-c:a", "aac", str(out)],
        check=True)


def _fmt(sec: float) -> str:
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:05.2f}"


def write_report(out_md: Path, silence_drops, judge_cuts, keeps, orig_dur, new_dur):
    lines = ["# 剪輯判斷對照表", "",
             f"- 原片長:{_fmt(orig_dur)} → 成品:{_fmt(new_dur)}(剪掉 {_fmt(orig_dur - new_dur)})",
             f"- 保留段數:{len(keeps)}", "", "## 剪掉的區間", ""]
    entries = [(s, e, "靜音") for s, e in silence_drops] + [
        (c["start"], c["end"], f"判官:{c['reason']}") for c in judge_cuts]
    for s, e, why in sorted(entries):
        lines.append(f"- {_fmt(s)} – {_fmt(e)}:{why}")
    if not entries:
        lines.append("(無)")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_cut(video: Path, settings: dict, auto_judge: bool = True, force: bool = False) -> int:
    outdir = output_dir(video)
    clean = outdir / "clean.mp4"
    if clean.exists() and not force:
        print(f"skip(已存在): {clean}")
        return 0

    duration = media_duration(video)
    sil = settings["silence"]
    silences = detect_silences(video, sil["noise_db"], sil["min_silence_sec"])
    silence_drops = silences_to_drops(silences, sil["keep_silence_sec"], duration)

    hw = config.load_hotwords()
    segments = transcribe(video, settings, hw["hotwords"])
    save_transcript(segments, outdir / "transcript.json")

    judge_cuts = []
    script_file = video.with_suffix(".txt")
    if auto_judge and script_file.exists() and shutil.which("claude"):
        from ytp.judge import build_judge_request, judge_retakes
        req = build_judge_request(segments, script_file.read_text(), silences)
        judge_cuts = judge_retakes(req, workdir=outdir)
    elif auto_judge:
        print("提示:無腳本或無 claude CLI,只剪靜音")

    drops = silence_drops + [(c["start"], c["end"]) for c in judge_cuts]
    keeps = merge_drops(drops, duration, settings["cut"]["min_keep_sec"])
    execute_cut(video, keeps, clean, settings)
    new_dur = media_duration(clean)
    write_report(outdir / "cut_report.md", silence_drops, judge_cuts, keeps, duration, new_dur)
    print(f"完成: {clean}({_fmt(duration)} → {_fmt(new_dur)}),對照表: {outdir / 'cut_report.md'}")
    return 0


def cmd_srt(video: Path, settings: dict, force: bool = False) -> int:
    """對淨毛片(沒有就原片)轉字幕。"""
    outdir = output_dir(video)
    srt = outdir / "subtitles.srt"
    if srt.exists() and not force:
        print(f"skip(已存在): {srt}")
        return 0
    src = outdir / "clean.mp4"
    if not src.exists():
        src = video
    hw = config.load_hotwords()
    segments = transcribe(src, settings, hw["hotwords"])
    write_srt(segments, srt, hw["replacements"])
    print(f"完成: {srt}")
    return 0
