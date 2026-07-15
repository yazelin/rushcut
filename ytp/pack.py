"""上架包文案:transcript + 頻道設定 → Claude → titles/description/social/seo。"""
import json
import re
import subprocess
from pathlib import Path

from ytp import config
from ytp.cut import output_dir
from ytp.transcribe import load_transcript

PROMPT = """你是 YouTube 頻道的文案編輯。根據影片逐字稿與頻道設定,產出上架包。
全部繁體中文(台灣用語),嚴格遵守頻道設定中的禁用詞。

只輸出純 JSON(不要 markdown fence、不要其他文字),格式:
{
  "titles": ["10 個候選標題,角度多樣:數字型、痛點型、好奇型、教學型"],
  "description": "YouTube 描述:第一行 hook、內容重點條列、結尾固定資訊",
  "social": "一則社群貼文(FB 風格,正文不放 URL)",
  "seo": ["8-15 個 SEO 關鍵字"]
}

## 頻道設定
{channel}

## 影片逐字稿
{transcript}
"""


def _extract_json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"pack 輸出找不到 JSON: {raw[:200]!r}")
    data = json.loads(m.group(0))
    missing = {"titles", "description", "social", "seo"} - set(data)
    if missing:
        raise ValueError(f"pack 輸出缺欄位: {missing}")
    return data


def generate_pack(transcript_text: str, channel: str, claude_bin: str = "claude") -> dict:
    prompt = PROMPT.replace("{channel}", channel or "(未設定,用中性口吻)").replace(
        "{transcript}", transcript_text)
    last_err = None
    for _ in range(2):
        proc = subprocess.run([claude_bin, "-p", prompt], capture_output=True, text=True, timeout=300)
        try:
            return _extract_json(proc.stdout)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
    raise RuntimeError(f"pack 兩次輸出皆非法: {last_err}")


def cmd_pack(video: Path, settings: dict, force: bool = False, claude_bin: str = "claude") -> int:
    outdir = output_dir(video)
    titles_md = outdir / "titles.md"
    if titles_md.exists() and not force:
        print(f"skip(已存在): {titles_md}")
        return 0
    tj = outdir / "transcript.json"
    if not tj.exists():
        print(f"錯誤:先跑 ytp cut(缺 {tj})")
        return 1
    transcript_text = "\n".join(s["text"] for s in load_transcript(tj))
    data = generate_pack(transcript_text, config.load_channel(), claude_bin)

    titles_md.write_text(
        "# 候選標題(選一個)\n\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(data["titles"], 1)) + "\n",
        encoding="utf-8")
    (outdir / "description.md").write_text(data["description"] + "\n", encoding="utf-8")
    (outdir / "social.md").write_text(data["social"] + "\n", encoding="utf-8")
    (outdir / "seo.md").write_text("\n".join(data["seo"]) + "\n", encoding="utf-8")
    print(f"完成: {outdir}/titles.md description.md social.md seo.md")
    return 0
