# SETUP

## 前置需求

1. **Python 3.10+**
2. **ffmpeg / ffprobe**(系統 PATH)
   - Ubuntu:`sudo apt install ffmpeg`
   - Windows:下載 [gyan.dev builds](https://www.gyan.dev/ffmpeg/builds/),把 `bin` 加進 PATH
3. **Claude Code CLI**(選用,但判官與文案需要):<https://claude.com/claude-code>
   - 沒裝也能用:`ytp cut --no-judge` 只剪靜音,pack 會跳過

## 安裝

```bash
git clone https://github.com/yazelin/rushcut && cd rushcut
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/ytp init
```

`ytp init` 會把範本複製到 `~/.config/rushcut/`,四個檔案都改成你自己的(見 README「個人化」)。

## GPU

faster-whisper 走 CTranslate2:有 NVIDIA GPU 自動用,失敗自動退 CPU(int8),不用另外裝 torch。
第一次跑會下載 whisper 模型(預設 `large-v3` 約 3GB;機器弱可在 settings.json 改 `"model_size": "small"`)。

## 使用

```bash
# 單支影片,毛片旁放同名腳本 txt(強烈建議,重講偵測會準很多)
.venv/bin/ytp cut raw/demo/video.mp4     # 順剪
.venv/bin/ytp srt raw/demo/video.mp4     # 字幕
.venv/bin/ytp pack raw/demo/video.mp4    # 標題/描述/社群/SEO
.venv/bin/ytp shorts raw/demo/video.mp4 --start 12 --end 42

# 或整個資料夾一次跑(冪等,重跑只補缺的;--force 全部重做)
.venv/bin/ytp run raw/demo/
```

產物都在影片旁的 `output/<影片名>/`。

## 測試

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/python tests/make_fixture.py   # 產合成測試毛片
.venv/bin/pytest -q
```
