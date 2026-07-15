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
