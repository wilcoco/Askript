"""배경 생성 및 자막 프레임 합성 (Pillow)."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from .models import Background

Size = Tuple[int, int]


# ---------------------------------------------------------------------------
# 배경
# ---------------------------------------------------------------------------
def make_background(bg: Background, size: Size) -> Image.Image:
    if bg.kind == "color":
        return Image.new("RGB", size, bg.color)
    if bg.kind == "gradient":
        return _gradient(bg.color, bg.color2 or bg.color, size)
    if bg.kind == "image":
        if not bg.image_path:
            raise ValueError("image 배경에는 image_path 가 필요합니다.")
        return _cover_image(bg.image_path, size)
    raise ValueError(f"알 수 없는 배경 종류: {bg.kind}")


def _gradient(top: tuple, bottom: tuple, size: Size) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(
            int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)
        )
    return base.resize(size)


def _cover_image(path: str, size: Size) -> Image.Image:
    img = Image.open(path).convert("RGB")
    w, h = size
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh))
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


# ---------------------------------------------------------------------------
# 텍스트 줄바꿈
# ---------------------------------------------------------------------------
def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    lines: List[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if font.getlength(trial) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
            current = ""
        if font.getlength(word) > max_width:
            # 한 단어가 너무 길면 글자 단위로 자른다.
            chunk = ""
            for ch in word:
                if font.getlength(chunk + ch) <= max_width:
                    chunk += ch
                else:
                    if chunk:
                        lines.append(chunk)
                    chunk = ch
            current = chunk
        else:
            current = word
    if current:
        lines.append(current)
    return lines or [""]


@lru_cache(maxsize=8)
def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------------------
# 프레임 합성
# ---------------------------------------------------------------------------
def compose_frame(
    background: Image.Image,
    font_path: str,
    subtitle: Optional[str] = None,
    title: Optional[str] = None,
) -> Image.Image:
    """배경 위에 제목(상단)과 자막(하단)을 그린 한 프레임을 반환."""
    img = background.convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 제목 (상단 중앙)
    if title:
        tf = _font(font_path, max(28, int(h * 0.072)))
        lines = wrap_text(title, tf, int(w * 0.86))
        _draw_centered_block(
            draw,
            lines,
            tf,
            w,
            top=int(h * 0.10),
            fill=(255, 255, 255),
            stroke=(0, 0, 0),
            stroke_width=max(2, int(h * 0.004)),
        )

    # 자막 (하단, 반투명 띠 위)
    if subtitle:
        sf = _font(font_path, max(24, int(h * 0.052)))
        lines = wrap_text(subtitle, sf, int(w * 0.86))
        line_h = int((sf.getbbox("가힣Ag")[3] - sf.getbbox("가힣Ag")[1]) * 1.45)
        block_h = line_h * len(lines)
        pad_x, pad_y = int(w * 0.04), int(h * 0.03)
        band_top = h - block_h - pad_y * 2 - int(h * 0.06)
        # 반투명 배경 띠
        draw.rectangle(
            [0, band_top, w, band_top + block_h + pad_y * 2],
            fill=(0, 0, 0, 140),
        )
        _draw_centered_block(
            draw,
            lines,
            sf,
            w,
            top=band_top + pad_y,
            fill=(255, 255, 255),
            stroke=(0, 0, 0),
            stroke_width=max(2, int(h * 0.003)),
            line_h=line_h,
        )

    return Image.alpha_composite(img, overlay).convert("RGB")


def _draw_centered_block(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    width: int,
    top: int,
    fill: tuple,
    stroke: tuple,
    stroke_width: int,
    line_h: Optional[int] = None,
) -> None:
    if line_h is None:
        bbox = font.getbbox("가힣Ag")
        line_h = int((bbox[3] - bbox[1]) * 1.4)
    y = top
    for line in lines:
        tw = font.getlength(line)
        x = (width - tw) / 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke,
        )
        y += line_h
