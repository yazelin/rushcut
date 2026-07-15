# rushcut

毛片 → YouTube 上架包,一條 CLI 搞定:**順剪**(去靜音、去重講/講壞)、**字幕**、**10 個候選標題**、**描述/社群文/SEO**、**Shorts 直式輸出**。

確定性的工作(ffmpeg、語音辨識、檔案編排)由 Python 做;需要「判斷」的工作(哪段是重講、標題文案)交給 Claude——每一刀都附理由,落地成人可複核的「剪輯判斷對照表」。全自動,但可驗收。

## 流程

```
raw 毛片 video.mp4 (+ 同名 video.txt 腳本,選放)
   │ ytp cut      → clean.mp4 + cut_report.md(每刀理由)+ transcript.json
   │ ytp srt      → subtitles.srt(hotwords 錯字修正 + 簡轉繁)
   │ ytp pack     → titles.md(10 候選)/ description.md / social.md / seo.md
   │ ytp shorts   → shorts.mp4(9:16)
   └ ytp run      → 上面全部串起來,冪等(已有產物自動跳過)
```

上傳 YouTube 刻意不做:成品在 `output/<影片名>/`,發佈永遠由人拍板。

## 安裝

見 [SETUP.md](SETUP.md)。三分鐘版:

```bash
git clone https://github.com/yazelin/rushcut && cd rushcut
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/ytp init          # 產生 ~/.config/rushcut/ 個人設定
.venv/bin/ytp run 你的資料夾/
```

需要:Python 3.10+、系統 ffmpeg、[Claude Code](https://claude.com/claude-code) CLI(判官與文案;沒有的話仍可 `--no-judge` 只剪靜音)。

## 個人化

設定全部在 `~/.config/rushcut/`,不進 repo:

| 檔案 | 用途 |
|---|---|
| `settings.json` | whisper 模型、靜音門檻、剪輯參數(全是可調旋鈕) |
| `hotwords.json` | 專有名詞 + 「辨識常錯 → 正確」替換表 |
| `channel.md` | 頻道定位、口吻、禁用詞(文案生成會遵守) |
| `cover-style.md` | 封面色票/構圖/字體規則(操作員生圖時遵循) |

## 設計出處

概念參考兩個來源(僅取設計,無程式碼複製):[mathruffian-dot/2026-YouTube](https://github.com/mathruffian-dot/2026-YouTube) 的上架包分段,以及「度哥自動順剪工具」的腳本比對抓重講、LLM 判官與剪輯對照表思路。

## Demo

`docs/demo/` 有一支合成毛片(edge-tts 唸稿,故意重講+長停頓)跑完全 pipeline 的實際產物。

## 授權 License

MIT © 2026 林亞澤 (Yaze Lin)

---

由 **林亞澤 Yaze Lin** 開發。覺得有用,歡迎分享,或請我喝杯咖啡。

- 原始碼 GitHub:<https://github.com/yazelin/rushcut>
- Facebook:<https://www.facebook.com/yaze.lin.gm>
- Buy Me a Coffee:<https://buymeacoffee.com/yazelin>
