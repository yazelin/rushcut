"""合成測試毛片:edge-tts 唸稿 + 故意重講 + 長停頓 + 純色畫面。

產出 tests/fixtures/demo/video.mp4 與 video.txt(最終腳本)。
"""
import asyncio
import subprocess
import sys
from pathlib import Path

import edge_tts

VOICE = "zh-TW-HsiaoChenNeural"
FIX = Path(__file__).parent / "fixtures" / "demo"

# (檔名, 內容) — B_bad 是講壞斷掉的重講,最終腳本裡只有完整版
LINES = [
    ("a", "大家好,今天要示範的是自動順剪工具,它可以把毛片變成乾淨的成品。"),
    ("b_bad", "這個工具會自動找出,呃,這個工具會自動"),
    ("b", "這個工具會自動找出重講和卡頓的段落,直接幫你剪掉。"),
    ("c", "接下來我們看看實際剪出來的效果,謝謝大家。"),
]

# 音軌組裝:句子與中間的靜音秒數
SEQUENCE = ["a", 2.5, "b_bad", 0.8, "b", 3.0, "c"]

SCRIPT = "\n".join(t for k, t in LINES if not k.endswith("_bad"))


async def tts(text: str, out: Path):
    await edge_tts.Communicate(text, VOICE).save(str(out))


def sh(*args):
    subprocess.run(args, check=True, capture_output=True)


def main():
    FIX.mkdir(parents=True, exist_ok=True)
    for key, text in LINES:
        mp3 = FIX / f"{key}.mp3"
        if not mp3.exists():
            asyncio.run(tts(text, mp3))

    # 每段轉成一致格式的 wav(含靜音段),再 concat
    parts = []
    for i, item in enumerate(SEQUENCE):
        wav = FIX / f"part{i}.wav"
        if isinstance(item, float):
            sh("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
               "-t", str(item), str(wav))
        else:
            sh("ffmpeg", "-y", "-i", str(FIX / f"{item}.mp3"), "-ar", "24000", "-ac", "1", str(wav))
        parts.append(wav)

    concat_list = FIX / "concat.txt"
    concat_list.write_text("".join(f"file '{p.name}'\n" for p in parts))
    audio = FIX / "audio.wav"
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(audio))

    # 純色靜態畫面配音軌
    video = FIX / "video.mp4"
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1280x720:r=24",
       "-i", str(audio), "-shortest", "-c:v", "libx264", "-preset", "veryfast",
       "-c:a", "aac", str(video))

    (FIX / "video.txt").write_text(SCRIPT + "\n")

    # 清中間檔
    for p in parts + [concat_list]:
        p.unlink()

    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True).stdout.strip()
    print(f"fixture 完成: {video} ({dur}s)")


if __name__ == "__main__":
    sys.exit(main())
