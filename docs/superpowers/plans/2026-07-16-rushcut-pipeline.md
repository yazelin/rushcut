# rushcut Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 毛片 → YouTube 上架包(淨毛片、字幕、標題、描述、社群文、Shorts)全自動 CLI,判斷節點交給 Claude。

**Architecture:** Python package `ytp`,每個 pipeline 段一個模組、一個 CLI 子命令,deterministic 工作(ffmpeg、STT、檔案編排)在 Python,判斷(重講剪點、文案)透過 `claude -p` headless 呼叫。個人設定外置 `~/.config/rushcut/`。

**Tech Stack:** Python 3.12、faster-whisper(CTranslate2)、ffmpeg(系統)、opencc-python-reimplemented、edge-tts(僅測試 fixture)、claude CLI。

## Global Constraints

- Python >= 3.10;ffmpeg/ffprobe 走系統 PATH
- MIT LICENSE,著作權人「林亞澤 (Yaze Lin)」
- 所有對外文字繁體中文;禁用詞見 `~/.config/rushcut/channel.md`(文案禁用詞:「接住」等)
- 個人資產(hotwords、頻道設定、封面風格、人物照)不進 git;repo 只放 `templates/` 範本
- 每段冪等:輸出存在即跳過,`--force` 重做
- 判官輸出必附理由,落地 `cut_report.md`
- README 要有推廣 footer(GitHub/FB/BMC 三連結)
- venv 在 repo 內 `.venv/`,`pip install -e .`

## File Structure

```
rushcut/
  pyproject.toml
  LICENSE  README.md  SETUP.md  .gitignore
  ytp/
    __init__.py     # __version__
    cli.py          # argparse dispatch: init/cut/srt/pack/shorts/run
    config.py       # DEFAULTS + ~/.config/rushcut merge; ytp init
    silence.py      # ffmpeg silencedetect → drop intervals
    transcribe.py   # faster-whisper wrapper → segments(words) ; SRT writer + hotwords + opencc
    judge.py        # judge_request 組裝、claude -p 呼叫、cut_plan 解析
    cut.py          # drops 合併→keep intervals→ffmpeg trim/concat + cut_report.md
    pack.py         # claude -p → titles/description/social/seo
    shorts.py       # 9:16 crop
    run.py          # orchestrate all, idempotent
  templates/
    settings.json  hotwords.json  channel.md  cover-style.md
  skills/rushcut/SKILL.md   # Claude Code 操作員工作流(含封面步驟)
  tests/
    make_fixture.py          # edge-tts 合成毛片(含重講+長停頓)+ 腳本 txt
    test_units.py            # 純函式測試(不需模型/claude)
    test_pipeline.py         # fixture 整條 E2E(需模型;judge/pack 測試在無 claude 時 skip)
```

---

### Task 1: Repo scaffold + CLI 骨架

**Files:** Create `pyproject.toml`, `LICENSE`, `.gitignore`, `ytp/__init__.py`, `ytp/cli.py`

**Produces:** `ytp` console script;`main()` argparse,子命令 stub。

- [ ] pyproject:name rushcut、deps `faster-whisper>=1.0`, `opencc-python-reimplemented>=0.1.7`;`[project.optional-dependencies] dev = ["edge-tts>=6.1", "pytest>=8"]`;`[project.scripts] ytp = "ytp.cli:main"`
- [ ] `.gitignore`: `.venv/ __pycache__/ output/ raw/ tests/fixtures/ *.egg-info/`
- [ ] `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`
- [ ] 驗:`.venv/bin/ytp --help` 列出六個子命令
- [ ] Commit `feat: repo scaffold + ytp CLI 骨架`

### Task 2: config.py + ytp init

**Files:** Create `ytp/config.py`, `templates/settings.json`, `templates/hotwords.json`, `templates/channel.md`, `templates/cover-style.md`; Test `tests/test_units.py`

**Interfaces (Produces):**
- `load_settings() -> dict` — DEFAULTS 深合併 `~/.config/rushcut/settings.json`
- `load_hotwords() -> dict` — `{"hotwords": [...], "replacements": {...}}`,檔案不存在回空結構
- `config_dir() -> Path` — 尊重 `RUSHCUT_CONFIG` 環境變數(測試用),預設 `~/.config/rushcut`
- `cmd_init()` — 複製 templates 到 config_dir,不覆蓋既有檔

settings.json 內容(度哥參數當起點,全是校準旋鈕):

```json
{
  "model_size": "large-v3",
  "language": "zh",
  "silence": {"noise_db": -30, "min_silence_sec": 0.45, "keep_silence_sec": 0.3},
  "cut": {"min_keep_sec": 0.2, "crf": 18, "preset": "veryfast"},
  "shorts": {"width": 1080, "height": 1920}
}
```

- [ ] 測試:`RUSHCUT_CONFIG` 指到 tmp、`load_settings()` 給預設值、init 後檔案存在、使用者覆寫生效
- [ ] Commit `feat(config): 設定外置 ~/.config/rushcut + ytp init`

### Task 3: silence.py

**Files:** Create `ytp/silence.py`; Test `tests/test_units.py`

**Interfaces (Produces):**
- `detect_silences(video: Path, noise_db: float, min_silence_sec: float) -> list[tuple[float,float]]` — 跑 `ffmpeg -af silencedetect` 收 stderr
- `parse_silencedetect(stderr: str) -> list[tuple[float,float]]` — 純函式
- `silences_to_drops(silences, keep_silence_sec, duration) -> list[tuple[float,float]]` — 每段靜音頭尾各留 keep_silence_sec,短於 2*keep 的靜音不剪

- [ ] 測試 parse(餵假 stderr 文字)與 to_drops 邊界(片頭/片尾靜音、過短靜音)
- [ ] Commit `feat(silence): ffmpeg silencedetect 靜音偵測與 drop 區間`

### Task 4: 合成 fixture

**Files:** Create `tests/make_fixture.py`

**Produces:** `tests/fixtures/demo/video.mp4`(約 40–60 秒,1280x720 純色畫面)+ `video.txt`(最終腳本)。音軌結構:句 A → 2.5s 靜音 → 句 B 講壞(前半句斷掉)→ 0.8s → 句 B 完整重講 → 3s 靜音 → 句 C。用 edge-tts(zh-TW, HsiaoChenNeural)產各句 mp3,ffmpeg `anullsrc` 產靜音,concat 後配 `color=c=0x1a1a2e` 靜態畫面。

- [ ] `.venv/bin/python tests/make_fixture.py` 產出;ffprobe 驗 duration 在預期範圍
- [ ] Commit `test: edge-tts 合成毛片 fixture 生成器(含重講+長停頓)`

### Task 5: transcribe.py(STT + SRT)

**Files:** Create `ytp/transcribe.py`; Test `tests/test_units.py`(純函式)+ `tests/test_pipeline.py`(真模型)

**Interfaces (Produces):**
- `transcribe(media: Path, settings: dict) -> list[dict]` — faster-whisper,回 `[{"start","end","text","words":[{"start","end","word"}]}]`;`device="auto"` 失敗退 CPU int8;hotwords 餵 `initial_prompt`
- `apply_replacements(text: str, replacements: dict) -> str`
- `to_traditional(text: str) -> str` — opencc s2twp,缺套件原樣返回
- `write_srt(segments: list[dict], out: Path, replacements: dict)`

- [ ] 純函式測試:`apply_replacements`、`to_traditional`("视频"→"影片"或至少繁化)、`write_srt` 時間碼格式
- [ ] pipeline 測試:fixture 音軌用 `model_size=small` 轉出非空 segments
- [ ] Commit `feat(stt): faster-whisper 轉錄 + SRT + hotwords 替換 + 簡轉繁`

### Task 6: judge.py(Claude 判官)

**Files:** Create `ytp/judge.py`; Test `tests/test_units.py`

**Interfaces (Produces):**
- `build_judge_request(segments, script_text: str|None, silences) -> dict`
- `parse_cut_plan(raw: str) -> list[dict]` — 容忍 ```json fence;每項 `{"start","end","reason"}`;非法 raise ValueError
- `judge_retakes(request: dict, claude_bin="claude") -> list[dict]` — `claude -p` 一次重試,兩次失敗留 `judge_request.json` 並 raise

判官 prompt(嵌在模組常數):給編號分句(含時間)與腳本,要求找出「重講只留最後一次、講壞、無意義填充」,輸出純 JSON array,每刀附 reason,無可剪回 `[]`。

- [ ] 測試:parse 容忍 fence/雜訊前綴;build_request 結構
- [ ] Commit `feat(judge): Claude 順剪判官協定(request/plan JSON + claude -p)`

### Task 7: cut.py(執行剪輯 + 對照表)

**Files:** Create `ytp/cut.py`; Test `tests/test_units.py`(merge 純函式)+ `tests/test_pipeline.py`

**Interfaces (Produces):**
- `merge_drops(drops: list[tuple], duration: float, min_keep_sec: float) -> list[tuple[float,float]]` — 重疊 drop 合併→取補集 keep;短於 min_keep 的 keep 併回丟棄
- `execute_cut(video: Path, keeps, out: Path, settings)` — filter_complex trim+concat(video+audio)
- `write_report(out_md: Path, silence_drops, judge_cuts, keeps, orig_dur, new_dur)` — cut_report.md:每刀起訖+理由(靜音/判官 reason)+ 前後時長
- `cmd_cut(video: Path, settings, auto_judge: bool)` — 組合;有同名 `.txt` 腳本才跑判官;輸出 `output/<name>/clean.mp4` + `cut_report.md` + `transcript.json`

- [ ] 測試 merge_drops:重疊合併、min_keep 過濾、無 drop 時整段保留
- [ ] pipeline 測試:fixture 跑 `cmd_cut`(auto_judge=claude 可用才開),clean.mp4 時長 < 原片,報表存在
- [ ] Commit `feat(cut): 順剪執行 + 剪輯判斷對照表`

### Task 8: pack.py(標題/描述/社群/SEO)

**Files:** Create `ytp/pack.py`; Test `tests/test_pipeline.py`(無 claude 則 skip)

**Interfaces (Produces):**
- `cmd_pack(video: Path, settings)` — 讀 `output/<name>/transcript.json` + config 的 `channel.md`,一次 `claude -p` 產 JSON `{titles:[10], description, social, seo:[...]}`,落地 `titles.md / description.md / social.md / seo.md`

prompt 要求:繁體中文、遵守 channel.md 禁用詞、標題 10 個含不同角度(數字/痛點/好奇/教學)。

- [ ] 測試:mock claude(monkeypatch subprocess)驗檔案落地與 10 標題;有真 claude 時 E2E
- [ ] Commit `feat(pack): 上架包文案生成(titles/description/social/seo)`

### Task 9: shorts.py

**Files:** Create `ytp/shorts.py`; Test `tests/test_pipeline.py`

**Interfaces (Produces):**
- `cmd_shorts(video: Path, start: float, end: float, settings)` — 取段→`crop=ih*9/16:ih` 置中→scale 1080x1920→`output/<name>/shorts.mp4`

- [ ] 測試:ffprobe 驗輸出 1080x1920、時長≈end-start
- [ ] Commit `feat(shorts): 9:16 直式片段輸出`

### Task 10: run.py + CLI 接線 + 冪等

**Files:** Create `ytp/run.py`; Modify `ytp/cli.py`

**Interfaces (Produces):**
- `cmd_run(folder: Path, settings, force: bool)` — 掃 `folder` 下影片,依序 cut→srt→pack,各段輸出存在即印 `skip`(force 重做);cover/shorts 留給操作員(印提示)

- [ ] E2E:fixture 資料夾跑 `ytp run`,第二次全 skip
- [ ] Commit `feat(run): 全 pipeline orchestration + 冪等`

### Task 11: 操作員 skill + 文件 + 範本內容

**Files:** Create `skills/rushcut/SKILL.md`, `README.md`, `SETUP.md`;補 `templates/channel.md`, `templates/cover-style.md` 實質內容

- SKILL.md:操作員流程(raw/ 放片→`ytp run`→讀 titles.md 請 user 選→用生圖工具照 cover-style.md 產 cover.png→選段跑 shorts)。封面是操作員步驟,CLI 不生圖。
- README:定位、示意流程、SETUP 連結、設計出處說明(參考 2026-YouTube 與順剪工具的「概念」)、推廣 footer(GitHub/FB/BMC)。
- [ ] Commit `docs: README/SETUP/操作員 skill + 範本`

### Task 12: 建 GitHub repo + demo 證據

- [ ] `gh repo create yazelin/rushcut --public --source . --push`
- [ ] fixture 全 pipeline 真跑一次(含 claude 判官與 pack),把文字類產物(cut_report.md、subtitles.srt、titles.md、description.md、social.md、seo.md)複製到 `docs/demo/` 進 git;影片產物留本機路徑寫進 demo README
- [ ] 封面:操作員步驟真跑一次(nanobanana)產 `docs/demo/cover.png`
- [ ] 全部測試綠 → push
- [ ] Commit `docs(demo): 合成毛片全 pipeline 實跑證據`

## Self-Review

- Spec 覆蓋:cut/srt/pack/shorts/run/init 全對應;上傳不做(spec 明列不做);封面=操作員步驟(Task 11/12)✓
- 型別一致:segments dict 結構在 Task 5 定義、6/7/8 消費一致 ✓
- 無 placeholder ✓
