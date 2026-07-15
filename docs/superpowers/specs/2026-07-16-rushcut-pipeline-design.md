# rushcut — YouTube 產製 pipeline 設計

日期:2026-07-16
狀態:已核准(yazelin 指示今晚完成,明早驗收)

## 目的

把「毛片 → 可上架的 YouTube 內容包」自動化。涵蓋兩種輸入:真人對鏡頭錄影(需順剪:去靜音、去重講/講壞)與螢幕錄影 demo(只需去靜音+字幕)。停在上架包,不做 API 上傳;上傳與經營留人工。

參考來源(只取設計,不取 code):

- `mathruffian-dot/2026-YouTube`(無 LICENSE):上架包 pipeline 的分段——剪輯/字幕/標題/封面/描述/Shorts。
- 度哥自動順剪工具(PyArmor 混淆,學生分享版):順剪設計——腳本 diff 抓重講、LLM 判官、剪輯判斷對照表、hotwords 錯字替換、冪等跳過。

## 定案決策

| 決策點 | 定案 |
|---|---|
| 架構 | 方案 A:Python CLI 骨架 + Claude 當判官(deterministic 歸 Python,判斷歸 AI) |
| STT | 單引擎 faster-whisper(word timestamps);剪點精度不足再加 funasr Paraformer(升級路徑,不先做) |
| 範圍 | 全 pipeline:順剪+字幕+標題+封面+描述+Shorts;停在上架包 |
| 上傳 | 不進 MVP,人工上傳 |
| repo | public,MIT 林亞澤;個人資產(hotwords、人物照、品牌色票)外置 `~/.config/rushcut/`,不進 git |
| 判官 LLM | Claude(`claude -p` headless 或 Claude Code 操作員 in-session),不申請額外金鑰 |
| 封面生圖 | 操作員步驟(Claude Code 用 nanobanana/codex-imagegen),CLI 只負責檢查檔案就位 |
| 驗收素材 | 合成測試片(edge-tts 唸稿+故意重講+長停頓+靜態畫面);真人素材驗收待 yazelin 錄 |

## CLI 介面

一支 `ytp` 命令(Python,repo 內 venv),子命令對應 pipeline 段:

```
ytp cut <video>       # 順剪:靜音偵測 + (有腳本時)重講判官 → 淨毛片 + 剪輯對照表
ytp srt <video>       # faster-whisper → SRT + hotwords 替換 + opencc 簡轉繁
ytp pack <video>      # 產 Claude 判官任務檔 → 標題x10/描述/社群文/SEO(JSON in, files out)
ytp shorts <video> --start --end   # 指定段落轉 9:16 直式
ytp run <folder>      # 串全 pipeline,冪等(已有產物跳過)
```

## 資料流

```
raw/<代號>/video.mp4 (+ video.txt 腳本,選放)
  → [cut] ffmpeg silencedetect 找靜音段
          + faster-whisper transcript(word timestamps)
          + 腳本 diff + Claude 判官 → cut_plan.json(每刀:起訖、理由)
          → ffmpeg 執行 → output/<代號>/clean.mp4 + cut_report.md(人可複核)
  → [srt] 淨毛片重轉字幕 → subtitles.srt(hotwords 替換 + 簡轉繁)
  → [pack] transcript + 頻道設定 → Claude → titles.md(10 候選)、description.md、social.md、seo.md
  → [cover] 操作員步驟:Claude Code 讀 cover-style.md + 選定標題 → 生圖 → cover.png
  → [shorts] 選段 → shorts.mp4(9:16)
```

判官協定:CLI 產生 `judge_request.json`(transcript 分句 + 腳本 + 靜音段),Claude 回 `cut_plan.json`;`ytp cut --auto` 直接內部呼叫 `claude -p`。判官永遠輸出理由,寫進 `cut_report.md`——全自動剪輯必須可複核。

## 個人設定(`~/.config/rushcut/`)

- `settings.json` — 模型大小、靜音門檻(noise_db/min_silence_sec/keep_silence_sec 等,全部外置可調,實體世界需要校準旋鈕)、ffmpeg crf/preset
- `hotwords.json` — hotwords + 「Whisper 常錯 → 正確」替換表
- `channel.md` — 頻道定位、口吻、禁用詞(接文案禁用詞政策)
- `cover-style.md` — 封面色票、構圖、字體規則
- repo 內附 `templates/` 範本,`ytp init` 複製到 `~/.config/rushcut/`

## 錯誤處理

- 每段獨立可跑、冪等:輸出已存在即跳過(`--force` 重做)
- 判官回傳非法 JSON → 重試一次,再失敗留 `judge_request.json` 給人工
- 無腳本 → 跳過重講偵測,只做靜音剪(降級不失敗)
- 無 GPU → ctranslate2 自動退 CPU,慢但能跑

## 測試與驗收

- 合成 fixture:edge-tts 產「正常句、重講兩次的句、3 秒停頓」音軌 + ffmpeg 靜態畫面 → `tests/fixtures/`(生成腳本進 repo,產物不進 git)
- `tests/test_pipeline.py`:靜音段被剪、重講只留最後一次、SRT 非空且繁體、冪等跳過——assert 式,不用重框架
- 明早驗收物:repo + 合成片跑完的 `output/` 全套(clean.mp4、cut_report.md、subtitles.srt、titles.md、description.md、social.md、cover.png、shorts.mp4)

## 不做(YAGNI)

- YouTube Data API 上傳、成效分析、留言回覆
- 雙 STT 引擎、GUI、web UI
- 多人/多頻道支援

## 公開 repo 檢查表

- MIT LICENSE(林亞澤)、README(含推廣 footer:GitHub/FB/BMC)、SETUP 說明、範本設定
