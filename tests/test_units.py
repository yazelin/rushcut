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
