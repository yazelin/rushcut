---
name: rushcut
description: 毛片 → YouTube 上架包。當 user 說「處理毛片」「順剪」「準備上架」「跑 rushcut」時使用:ytp run 跑完自動段後,操作員(你)接手選標題確認、生封面、選 Shorts 段落。
---

# rushcut 操作員工作流

你是 pipeline 的操作員。自動段交給 CLI,判斷與美術由你做。

## 前置

- repo 位置與 venv:`cd <rushcut repo> && .venv/bin/ytp --help`
- 個人設定在 `~/.config/rushcut/`(hotwords、channel.md、cover-style.md)

## 流程

1. **確認素材**:user 指定的資料夾裡有 `video.mp4`;問 user 有沒有腳本 txt(同名放旁邊,重講偵測準很多)。
2. **跑自動段**:`.venv/bin/ytp run <資料夾>`(冪等,可重跑)。
3. **複核剪輯**:讀 `output/<name>/cut_report.md`,把「剪了幾刀、剪掉多久、判官理由」摘要給 user;有可疑的刀就標出來。
4. **選標題**:讀 `output/<name>/titles.md`,把 10 個候選給 user 選(或 user 授權你選前 3 推薦)。
5. **生封面**(操作員步驟,CLI 不生圖):
   - 讀 `~/.config/rushcut/cover-style.md` 的色票/構圖/字體規則
   - 用可用的生圖工具(nanobanana / codex-imagegen)產 1280x720 封面
   - 中文標題字建議 canvas/後製疊字,不要指望生圖模型寫字
   - 存 `output/<name>/cover.png`
6. **Shorts**:和 user 挑精華段(看 transcript.json 時間),跑 `ytp shorts <video> --start S --end E`。
7. **交付**:列出 `output/<name>/` 全部產物路徑。上傳 YouTube 由 user 手動——不要代發佈。

## 注意

- 文案類產物已遵守 channel.md 禁用詞,但交付前再掃一次。
- 判官剪錯(誤殺正常段)時:把該刀從 cut_report.md 標出,手動改 settings 門檻或請 user 決定,`--force` 重跑。
