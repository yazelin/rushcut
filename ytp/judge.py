"""Claude 順剪判官:transcript+腳本 → 該剪的區間(每刀附理由)。"""
import json
import re
import subprocess
from pathlib import Path

PROMPT = """你是影片順剪判官。以下是一支毛片的逐段轉錄(含秒數)與拍攝腳本。
找出應該剪掉的區間:
1. 重講:同一句講了多次,只留「最後一次完整的」,前面的都剪掉。
2. 講壞:講到一半斷掉、口誤重來的殘句。
3. 無意義填充:長串的「呃、嗯、那個」開場殘段(句中自然語氣詞不算)。

規則:
- 用轉錄段落的 start/end 秒數當剪點,可以合併相鄰段落。
- 不確定的不要剪,寧可保守。
- 只輸出純 JSON array,不要任何其他文字。每項格式:
  {"start": 秒數, "end": 秒數, "reason": "為什麼剪(繁體中文)"}
- 沒有可剪的就輸出 []

## 拍攝腳本(最終想要的內容)
{script}

## 逐段轉錄
{segments}
"""


def build_judge_request(segments: list[dict], script_text: str | None, silences) -> dict:
    return {
        "script": (script_text or "").strip(),
        "segments": [
            {"i": i, "start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"]}
            for i, s in enumerate(segments)
        ],
        "silences": [[round(a, 2), round(b, 2)] for a, b in silences],
    }


def parse_cut_plan(raw: str) -> list[dict]:
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        raise ValueError(f"判官輸出找不到 JSON array: {raw[:200]!r}")
    plan = json.loads(m.group(0))
    if not isinstance(plan, list):
        raise ValueError("判官輸出不是 array")
    for cut in plan:
        if not {"start", "end", "reason"} <= set(cut):
            raise ValueError(f"剪點缺欄位: {cut}")
        cut["start"], cut["end"] = float(cut["start"]), float(cut["end"])
    return plan


def judge_retakes(request: dict, claude_bin: str = "claude", workdir: Path | None = None) -> list[dict]:
    prompt = PROMPT.replace("{script}", request["script"] or "(無腳本)").replace(
        "{segments}",
        "\n".join(f"[{s['i']}] {s['start']}–{s['end']}s: {s['text']}" for s in request["segments"]),
    )
    last_err = None
    for _ in range(2):
        proc = subprocess.run(
            [claude_bin, "-p", prompt], capture_output=True, text=True, timeout=300)
        try:
            return parse_cut_plan(proc.stdout)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
    if workdir:
        (workdir / "judge_request.json").write_text(
            json.dumps(request, ensure_ascii=False, indent=1), encoding="utf-8")
    raise RuntimeError(f"判官兩次輸出皆非法 JSON,request 已留檔: {last_err}")
