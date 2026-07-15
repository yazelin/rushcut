"""ytp — rushcut pipeline CLI。"""
import argparse
import sys
from pathlib import Path


def main(argv=None):
    p = argparse.ArgumentParser(prog="ytp", description="毛片 → YouTube 上架包 pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="複製範本設定到 ~/.config/rushcut/")

    for name, help_ in [
        ("cut", "順剪:去靜音 +(有腳本時)Claude 判官去重講"),
        ("srt", "淨毛片 → 字幕 SRT(hotwords 替換 + 簡轉繁)"),
        ("pack", "標題x10/描述/社群文/SEO"),
    ]:
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("video", type=Path)
        sp.add_argument("--force", action="store_true")
        if name == "cut":
            sp.add_argument("--no-judge", action="store_true", help="只剪靜音,不跑判官")

    sp = sub.add_parser("shorts", help="指定段落轉 9:16 直式")
    sp.add_argument("video", type=Path)
    sp.add_argument("--start", type=float, required=True)
    sp.add_argument("--end", type=float, required=True)

    sp = sub.add_parser("run", help="資料夾全 pipeline(冪等)")
    sp.add_argument("folder", type=Path)
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--no-judge", action="store_true")

    args = p.parse_args(argv)

    from ytp import config
    if args.cmd == "init":
        return config.cmd_init()

    settings = config.load_settings()
    if args.cmd == "cut":
        from ytp.cut import cmd_cut
        return cmd_cut(args.video, settings, auto_judge=not args.no_judge, force=args.force)
    if args.cmd == "srt":
        from ytp.cut import cmd_srt
        return cmd_srt(args.video, settings, force=args.force)
    if args.cmd == "pack":
        from ytp.pack import cmd_pack
        return cmd_pack(args.video, settings, force=args.force)
    if args.cmd == "shorts":
        from ytp.shorts import cmd_shorts
        return cmd_shorts(args.video, args.start, args.end, settings)
    if args.cmd == "run":
        from ytp.run import cmd_run
        return cmd_run(args.folder, settings, force=args.force, auto_judge=not args.no_judge)


if __name__ == "__main__":
    sys.exit(main())
