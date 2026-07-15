# Demo:合成毛片全 pipeline 實跑產物

素材:`tests/make_fixture.py` 用 edge-tts 合成的 29.3 秒毛片——四句話,其中一句**故意講壞斷掉再重講**,並穿插 2.5–3 秒長停頓。

跑 `ytp run raw/demo/` 後的實際產物(文字類收進這裡,影片類不進 git):

| 檔案 | 內容 |
|---|---|
| [cut_report.md](cut_report.md) | 剪輯判斷對照表:29.27s → 16.96s,判官抓到講壞重講段並附理由 |
| [subtitles.srt](subtitles.srt) | 淨毛片字幕(hotwords 修正 + 繁體) |
| [titles.md](titles.md) | 10 個候選標題 |
| [description.md](description.md) | YouTube 描述 |
| [social.md](social.md) | 社群貼文 |
| [seo.md](seo.md) | SEO 關鍵字 |
| [cover.png](cover.png) | 封面(操作員步驟:PIL 疊字,遵循 cover-style) |

影片產物(`clean.mp4`、`shorts.mp4`)在本機 `raw/demo/output/video/`,重跑一次 `ytp run` 即可再生。
