"""純函式測試:不需要模型、claude、ffmpeg 實跑。"""
import json

import pytest


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("RUSHCUT_CONFIG", str(tmp_path))
    return tmp_path


def test_load_settings_defaults(cfg):
    from ytp import config
    s = config.load_settings()
    assert s["silence"]["noise_db"] == -30
    assert s["model_size"] == "large-v3"


def test_init_then_override(cfg):
    from ytp import config
    config.cmd_init()
    assert (cfg / "settings.json").exists()
    (cfg / "settings.json").write_text(json.dumps({"model_size": "small", "silence": {"noise_db": -35}}))
    s = config.load_settings()
    assert s["model_size"] == "small"
    assert s["silence"]["noise_db"] == -35
    assert s["silence"]["min_silence_sec"] == 0.45  # 未覆寫的保留預設


def test_init_does_not_overwrite(cfg):
    from ytp import config
    (cfg / "hotwords.json").write_text('{"hotwords":["我的"],"replacements":{}}')
    config.cmd_init()
    assert config.load_hotwords()["hotwords"] == ["我的"]


def test_load_hotwords_missing(cfg):
    from ytp import config
    assert config.load_hotwords() == {"hotwords": [], "replacements": {}}


# --- silence ---

FAKE_STDERR = """
[silencedetect @ 0x1] silence_start: 5.2
[silencedetect @ 0x1] silence_end: 8.0 | silence_duration: 2.8
[silencedetect @ 0x1] silence_start: 20.0
"""


def test_parse_silencedetect_pairs_and_tail():
    from ytp.silence import parse_silencedetect
    got = parse_silencedetect(FAKE_STDERR)
    assert got[0] == (5.2, 8.0)
    assert got[1][0] == 20.0 and got[1][1] == float("inf")


def test_silences_to_drops_padding_and_edges():
    from ytp.silence import silences_to_drops
    drops = silences_to_drops([(5.2, 8.0), (20.0, float("inf"))], keep_silence_sec=0.3, duration=25.0)
    assert drops[0] == (5.5, 7.7)          # 兩側各留 0.3
    assert drops[1] == (20.3, 25.0)        # 片尾靜音剪到底
    # 過短靜音(留完呼吸感沒東西可剪)不產生 drop
    assert silences_to_drops([(1.0, 1.5)], keep_silence_sec=0.3, duration=10) == []
    # 片頭靜音從 0 開始剪
    assert silences_to_drops([(0.0, 3.0)], keep_silence_sec=0.3, duration=10) == [(0.0, 2.7)]


# --- transcribe 純函式 ---

def test_apply_replacements():
    from ytp.transcribe import apply_replacements
    assert apply_replacements("杜哥說銷售業", {"杜哥": "度哥", "銷售業": "銷售頁"}) == "度哥說銷售頁"


def test_to_traditional():
    from ytp.transcribe import to_traditional
    out = to_traditional("这个视频")
    assert "這" in out  # 至少繁化


def test_write_srt_format(tmp_path):
    from ytp.transcribe import write_srt
    segs = [{"start": 0.0, "end": 1.5, "text": "你好", "words": []},
            {"start": 61.25, "end": 62.0, "text": "再見", "words": []}]
    out = tmp_path / "s.srt"
    write_srt(segs, out)
    content = out.read_text()
    assert "00:00:00,000 --> 00:00:01,500" in content
    assert "00:01:01,250 --> 00:01:02,000" in content
    assert content.startswith("1\n")


# --- judge ---

def test_parse_cut_plan_tolerates_fences():
    from ytp.judge import parse_cut_plan
    raw = '好的,以下是結果:\n```json\n[{"start": 1.0, "end": 2.5, "reason": "重講"}]\n```'
    plan = parse_cut_plan(raw)
    assert plan == [{"start": 1.0, "end": 2.5, "reason": "重講"}]


def test_parse_cut_plan_empty_and_invalid():
    from ytp.judge import parse_cut_plan
    assert parse_cut_plan("[]") == []
    import pytest as _pt
    with _pt.raises(ValueError):
        parse_cut_plan("完全沒有 JSON")
    with _pt.raises(ValueError):
        parse_cut_plan('[{"start": 1.0}]')


def test_build_judge_request():
    from ytp.judge import build_judge_request
    segs = [{"start": 0.0, "end": 1.234, "text": "你好", "words": []}]
    req = build_judge_request(segs, "腳本", [(2.0, 3.0)])
    assert req["segments"][0] == {"i": 0, "start": 0.0, "end": 1.23, "text": "你好"}
    assert req["silences"] == [[2.0, 3.0]]


# --- cut.merge_drops ---

def test_merge_drops_overlap_and_minkeep():
    from ytp.cut import merge_drops
    # 重疊 drop 合併
    keeps = merge_drops([(1.0, 3.0), (2.5, 5.0)], duration=10.0, min_keep_sec=0.2)
    assert keeps == [(0.0, 1.0), (5.0, 10.0)]
    # 兩刀之間 keep 太短 → 併掉
    keeps = merge_drops([(1.0, 3.0), (3.1, 5.0)], duration=10.0, min_keep_sec=0.2)
    assert keeps == [(0.0, 1.0), (5.0, 10.0)]
    # 無 drop 全保留
    assert merge_drops([], 10.0, 0.2) == [(0.0, 10.0)]
