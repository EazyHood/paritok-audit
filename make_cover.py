# SPDX-License-Identifier: Apache-2.0
"""Render the submission cover image.

Devpost wants a project image and every submission in the gallery has one. The
obvious choice would be the headline savings number, but that is the number this
project exists to argue with. So the card leads with the ratio and then shows
what the ratio hides -- recall per category -- because that contrast is the whole
thesis in one picture.

Every figure here comes from REPORT.txt. Nothing is rounded for effect.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 675
BG = (13, 17, 23)
FG = (230, 237, 243)
DIM = (125, 133, 144)
GOOD = (63, 185, 80)
WARN = (210, 153, 34)
BAD = (248, 81, 73)
ACCENT = (88, 166, 255)

# Measured, single run, from REPORT.txt. Ordered worst-last so the eye lands
# on the categories that do not survive compression.
ROWS = [
    ("error strings", 90.9),
    ("identifiers", 43.4),
    ("hashes", 32.2),
    ("paths", 23.7),
    ("URLs", 20.8),
    ("numbers", 13.1),
    ("shell commands", 12.5),
]


def font(name: str, size: int):
    for candidate in (name, f"C:/Windows/Fonts/{name}"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def colour_for(pct: float):
    if pct >= 60:
        return GOOD
    if pct >= 30:
        return WARN
    return BAD


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    title = font("segoeuib.ttf", 44)
    sub = font("segoeui.ttf", 23)
    mono = font("consola.ttf", 26)
    mono_s = font("consola.ttf", 19)

    d.text((64, 56), "Context compression saved 78.3%", font=title, fill=FG)
    d.text(
        (64, 116),
        "of my tokens. Here is what it deleted.",
        font=title,
        fill=ACCENT,
    )

    d.text(
        (64, 186),
        "Recall by category, same corpus, same run. Compression ratio alone",
        font=sub,
        fill=DIM,
    )
    d.text(
        (64, 216),
        "cannot tell you a shell command is unlikely to survive the trip.",
        font=sub,
        fill=DIM,
    )

    y = 276
    bar_x, bar_w = 430, 480
    for label, pct in ROWS:
        d.text((64, y), label, font=mono, fill=FG)
        d.rectangle([bar_x, y + 8, bar_x + bar_w, y + 24], fill=(30, 36, 44))
        d.rectangle(
            [bar_x, y + 8, bar_x + int(bar_w * pct / 100), y + 24],
            fill=colour_for(pct),
        )
        d.text((bar_x + bar_w + 18, y), f"{pct:>5.1f}%", font=mono, fill=colour_for(pct))
        y += 46

    d.text(
        (64, H - 74),
        "paritok-audit  ·  Apache 2.0  ·  github.com/EazyHood/paritok-audit",
        font=mono_s,
        fill=DIM,
    )
    d.text(
        (64, H - 48),
        "Single-run measurements: the compressor is not deterministic (47.8% and 42.8% on identical input).",
        font=mono_s,
        fill=DIM,
    )

    out = pathlib.Path(__file__).with_name("cover.png")
    img.save(out)
    print(f"wrote {out}  ({W}x{H})")


if __name__ == "__main__":
    main()
