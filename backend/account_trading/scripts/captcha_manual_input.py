"""Manual captcha helper for THS desktop adapter screenshots.

This script intentionally does not perform OCR. It locates the latest
captcha screenshot, opens it for a human operator, then returns the code
typed by the operator so the trading workflow can continue explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_CAPTCHA_DIR = Path("docs") / "ths-desktop-adapter"
CAPTCHA_PATTERN = "captcha-*.png"


def find_latest_captcha(captcha_dir: Path) -> Path:
    files = sorted(
        captcha_dir.glob(CAPTCHA_PATTERN),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No {CAPTCHA_PATTERN} files found in {captcha_dir}")
    return files[0]


def open_image(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
        return

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen(
        [opener, str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def read_captcha_code(min_length: int, max_length: int) -> str:
    pattern = re.compile(rf"^\d{{{min_length},{max_length}}}$")
    while True:
        try:
            code = input("请输入图片中的验证码数字: ").strip()
        except EOFError as exc:
            raise RuntimeError("No captcha code was provided.") from exc
        if pattern.fullmatch(code):
            return code
        print(f"验证码必须是 {min_length}-{max_length} 位数字，请重新输入。", file=sys.stderr)


def validate_captcha_code(code: str, min_length: int, max_length: int) -> str:
    code = code.strip()
    pattern = re.compile(rf"^\d{{{min_length},{max_length}}}$")
    if not pattern.fullmatch(code):
        raise ValueError(f"Captcha code must be {min_length}-{max_length} digits.")
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open latest captcha screenshot and read manual input.")
    parser.add_argument(
        "--captcha-dir",
        type=Path,
        default=DEFAULT_CAPTCHA_DIR,
        help=f"Captcha screenshot directory. Default: {DEFAULT_CAPTCHA_DIR}",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Specific captcha image path. If omitted, the latest captcha-*.png is used.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the image viewer; only print/prompt.",
    )
    parser.add_argument("--min-length", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=6)
    parser.add_argument("--code", help="Manually recognized captcha code to validate and return.")
    parser.add_argument("--json", action="store_true", help="Print result as JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    captcha_path = args.file if args.file else find_latest_captcha(args.captcha_dir)
    captcha_path = captcha_path.resolve()
    if not captcha_path.exists():
        print(f"Captcha image not found: {captcha_path}", file=sys.stderr)
        return 2

    print(f"验证码图片: {captcha_path}", file=sys.stderr)
    if not args.no_open:
        open_image(captcha_path)

    if args.code:
        try:
            code = validate_captcha_code(args.code, args.min_length, args.max_length)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 3
    else:
        try:
            code = read_captcha_code(args.min_length, args.max_length)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 3
    if args.json:
        print(json.dumps({"captcha_path": str(captcha_path), "captcha_code": code}, ensure_ascii=False))
    else:
        print(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
