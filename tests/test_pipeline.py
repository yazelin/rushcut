"""E2E 測試:需要 fixture 與 whisper 模型;judge/pack 在 claude 不可用時 skip。

先跑 `python tests/make_fixture.py` 產 fixture。
測試用 small 模型(settings 覆寫),避免拉 large-v3。
"""
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "demo" / "video.mp4"

pytestmark = pytest.mark.skipif(not FIXTURE.exists(), reason="先跑 tests/make_fixture.py")

TEST_SETTINGS = {
    "model_size": "small",
    "language": "zh",
    "silence": {"noise_db": -30, "min_silence_sec": 0.45, "keep_silence_sec": 0.3},
    "cut": {"min_keep_sec": 0.2, "crf": 23, "preset": "veryfast"},
    "shorts": {"width": 1080, "height": 1920},
}


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


@pytest.fixture(scope="module")
def workdir(tmp_path_factory):
    d = tmp_path_factory.mktemp("demo")
    shutil.copy(FIXTURE, d / "video.mp4")
    shutil.copy(FIXTURE.with_suffix(".txt"), d / "video.txt")
    return d


def test_transcribe_fixture(workdir):
    from ytp.transcribe import transcribe
    segs = transcribe(workdir / "video.mp4", TEST_SETTINGS)
    assert segs, "轉錄不可為空"
    joined = "".join(s["text"] for s in segs)
    assert "順剪" in joined or "工具" in joined


def test_cut_silence_only(workdir):
    from ytp.cut import cmd_cut
    cmd_cut(workdir / "video.mp4", TEST_SETTINGS, auto_judge=False, force=True)
    out = workdir / "output" / "video" / "clean.mp4"
    report = workdir / "output" / "video" / "cut_report.md"
    assert out.exists() and report.exists()
    orig, new = ffprobe_duration(workdir / "video.mp4"), ffprobe_duration(out)
    assert new < orig - 2, f"至少剪掉 2 秒靜音 (orig={orig}, new={new})"


def test_srt_output(workdir):
    from ytp.cut import cmd_srt
    cmd_srt(workdir / "video.mp4", TEST_SETTINGS, force=True)
    srt = workdir / "output" / "video" / "subtitles.srt"
    assert srt.exists()
    content = srt.read_text()
    assert "-->" in content and len(content) > 50


def test_idempotent_skip(workdir, capsys):
    from ytp.cut import cmd_cut
    cmd_cut(workdir / "video.mp4", TEST_SETTINGS, auto_judge=False, force=False)
    assert "skip" in capsys.readouterr().out


def test_shorts(workdir):
    from ytp.shorts import cmd_shorts
    cmd_shorts(workdir / "video.mp4", 0.0, 5.0, TEST_SETTINGS)
    out = workdir / "output" / "video" / "shorts.mp4"
    assert out.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True)
    assert probe.stdout.strip() == "1080,1920"
    assert abs(ffprobe_duration(out) - 5.0) < 0.5


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI 不可用")
def test_judge_finds_retake(workdir):
    from ytp.judge import build_judge_request, judge_retakes
    from ytp.transcribe import transcribe
    segs = transcribe(workdir / "video.mp4", TEST_SETTINGS)
    req = build_judge_request(segs, (workdir / "video.txt").read_text(), [])
    cuts = judge_retakes(req)
    assert isinstance(cuts, list)
    assert cuts, "fixture 有明顯講壞重講,判官應至少提出一刀"
    for c in cuts:
        assert {"start", "end", "reason"} <= set(c)
