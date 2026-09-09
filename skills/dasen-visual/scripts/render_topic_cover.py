#!/usr/bin/env python3
"""Render the repository's optional dasen-editorial topic-cover preset."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    print("[error] Pillow 未安装：python3 -m pip install pillow", file=sys.stderr)
    raise SystemExit(2)

FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
    Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
)

COLORS = {
    "purple": "#7132F5",
    "deep_purple": "#5B1ECF",
    "soft_purple": "#F0E9FF",
    "text": "#0B0B12",
    "muted": "#6B6B7A",
    "line": "#E8E8ED",
    "dark": "#11131A",
}
PRESET_ID = "dasen-editorial"


def compact(value: str) -> str:
    return "".join(value.split())


def normalized_contains(line: str, label: str) -> bool:
    return compact(label).casefold() in compact(line).casefold()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render the optional dasen-editorial topic cover")
    p.add_argument("--preset", required=True, choices=[PRESET_ID])
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--topic-label", required=True)
    p.add_argument("--title", required=True, help="Exact article title")
    p.add_argument("--title-lines", required=True, help="Visual lines separated by |; text must equal --title")
    p.add_argument("--accent-line", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--feature", action="append", default=[], help="Card label or label::short proof; repeat 3–5 times")
    p.add_argument("--font", help="Optional .ttf/.ttc font path; required when no default CJK font exists")
    p.add_argument("--width", type=int, default=2000)
    p.add_argument("--height", type=int, default=850)
    return p


def load_font(path: Path, size: int, *, bold: bool) -> ImageFont.FreeTypeFont:
    if path.name == "Hiragino Sans GB.ttc":
        return ImageFont.truetype(str(path), size, index=2 if bold else 0)
    return ImageFont.truetype(str(path), size)


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def main() -> int:
    args = parser().parse_args()
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_file():
        print(f"[error] 输入图不存在：{source}", file=sys.stderr)
        return 2
    title_lines = [x.strip() for x in args.title_lines.split("|") if x.strip()]
    if not title_lines or compact("".join(title_lines)) != compact(args.title):
        print("[error] --title-lines 必须与 --title 逐字一致，只允许增加换行", file=sys.stderr)
        return 2
    if not 1 <= len(compact(args.topic_label)) <= 20:
        print("[error] topic label 长度异常", file=sys.stderr)
        return 2
    if not 3 <= len(args.feature) <= 5:
        print("[error] --feature 必须提供 3–5 次", file=sys.stderr)
        return 2
    font_path = Path(args.font).expanduser().resolve() if args.font else next(
        (p for p in FONT_CANDIDATES if p.is_file()), None
    )
    if font_path is None or not font_path.is_file():
        print("[error] 找不到可用中文黑体；请用 --font 指定", file=sys.stderr)
        return 2

    with Image.open(source) as raw:
        canvas = ImageOps.fit(
            raw.convert("RGB"),
            (args.width, args.height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.48),
        ).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    left_x = 48
    left_width = 835
    label_font = load_font(font_path, 42, bold=True)
    title_size = 72 if len(title_lines) <= 2 else 62 if len(title_lines) == 3 else 54
    title_font = load_font(font_path, title_size, bold=True)
    accent_font = load_font(font_path, 42, bold=True)
    summary_font = load_font(font_path, 30, bold=False)
    card_title_font = load_font(font_path, 25, bold=True)
    card_proof_font = load_font(font_path, 18, bold=False)

    label_w = min(max(text_width(draw, args.topic_label, label_font) + 120, 355), 720)
    draw.rounded_rectangle((left_x, 20, left_x + label_w, 132), radius=32, fill=COLORS["dark"])
    draw.ellipse((left_x + 25, 49, left_x + 79, 103), fill=COLORS["purple"])
    draw.ellipse((left_x + 39, 63, left_x + 65, 89), fill="#B79AFF")
    draw.text((left_x + 98, 48), args.topic_label, font=label_font, fill="#FFFFFF")

    y = 190
    for line in title_lines:
        if text_width(draw, line, title_font) > left_width:
            print(f"[error] 标题行超过文字安全区，请重新断行：{line}", file=sys.stderr)
            return 2
        color = COLORS["purple"] if normalized_contains(line, args.topic_label) else COLORS["text"]
        draw.text((left_x, y), line, font=title_font, fill=color)
        y += title_size + 10

    if text_width(draw, args.accent_line, accent_font) > left_width:
        print("[error] 强调句超过文字安全区", file=sys.stderr)
        return 2
    draw.text((left_x, y + 5), args.accent_line, font=accent_font, fill=COLORS["purple"])
    y += 62
    if text_width(draw, args.summary, summary_font) > left_width:
        print("[error] 说明超过文字安全区", file=sys.stderr)
        return 2
    draw.text((left_x + 2, y), args.summary, font=summary_font, fill=COLORS["muted"])

    card_y = 665
    card_gap = 16
    card_area_width = 704
    card_w = (card_area_width - card_gap * (len(args.feature) - 1)) // len(args.feature)
    for index, raw_feature in enumerate(args.feature):
        label, _, proof = raw_feature.partition("::")
        label, proof = label.strip(), proof.strip()
        if not label:
            print("[error] feature label 为空", file=sys.stderr)
            return 2
        x = left_x + index * (card_w + card_gap)
        draw.rounded_rectangle((x, card_y, x + card_w, 818), radius=20,
                               fill="#FFFFFF", outline=COLORS["line"], width=2)
        draw.ellipse((x + 12, card_y + 18, x + 34, card_y + 40), fill=COLORS["purple"])
        if text_width(draw, label, card_title_font) > card_w - 48:
            print(f"[error] feature label 太长：{label}", file=sys.stderr)
            return 2
        draw.text((x + 43, card_y + 10), label, font=card_title_font, fill=COLORS["text"])
        if proof:
            if text_width(draw, proof, card_proof_font) > card_w - 22:
                print(f"[error] feature proof 太长：{proof}", file=sys.stderr)
                return 2
            draw.text((x + 11, card_y + 89), proof, font=card_proof_font, fill=COLORS["muted"])

    final = canvas.convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    final.save(output, format="PNG", optimize=True)
    try:
        with Image.open(output) as image:
            if image.size != (args.width, args.height):
                print(f"[error] 输出尺寸错误：{image.size}", file=sys.stderr)
                return 3
            image.verify()
    except Exception as exc:
        print(f"[error] 输出图片无法验证：{exc}", file=sys.stderr)
        return 3
    print(f"ok: {output} ({args.width}x{args.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
