"""스크립트 텍스트를 Scene/Segment 구조로 파싱.

스크립트 형식 (UTF-8 텍스트):

  - 빈 줄로 장면(scene)을 구분합니다.
  - `@` 로 시작하는 줄은 그 장면의 지시어(directive)입니다.
  - 그 외의 줄은 내레이션 본문이며, 문장 단위로 자막/음성으로 나뉩니다.

지원 지시어:
  @bg color #1e2a44                단색 배경
  @bg gradient #001027 #0a3d91     그라데이션 배경
  @bg image path/to/img.png [fit]  로컬 이미지 배경
  @bg video path/to/clip.mp4 [fit] 로컬 동영상 배경
  @media path/to/file [fit]        이미지/동영상 자동 감지
  @search [image|video] 키워드      스톡(Pexels)에서 검색해 배경으로 사용
  @fit cover|contain               화면 맞춤 (꽉채움 / 잘림없이)
  @title 화면 상단에 표시할 제목
  @duration 5                      내레이션 없는 b-roll 장면 길이(초)
  @voice ko-KR-InJoonNeural        이 장면만 다른 목소리
  @rate +10%                       이 장면만 말하기 속도

  (fit 은 cover[기본]/contain. 다이어그램·스크린샷은 contain 권장)

예시:

  @bg gradient #001027 #0a3d91
  @title 오늘의 주제
  안녕하세요. 오늘은 인공지능에 대해 이야기합니다.
  인공지능은 우리 삶을 빠르게 바꾸고 있습니다.

  @bg color #101418
  두 번째 장면입니다. 배경이 바뀌었습니다.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .models import Background, Scene, Segment

# 문장 종료 부호 (한국어/영어/일반). 줄바꿈도 문장 경계로 취급.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？…])\s+")


def parse_color(text: str) -> tuple:
    """'#1e2a44' 또는 'r,g,b' 형태를 (r, g, b) 로 변환."""
    text = text.strip()
    if text.startswith("#"):
        h = text[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) != 6:
            raise ValueError(f"잘못된 색상 코드: {text}")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    if "," in text:
        parts = [int(p) for p in text.split(",")]
        if len(parts) != 3:
            raise ValueError(f"잘못된 색상: {text}")
        return tuple(parts)
    raise ValueError(f"색상을 해석할 수 없습니다: {text}")


_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
_FIT_VALUES = {"cover", "contain"}


def _split_fit(tokens: List[str], default: str = "cover"):
    """경로 토큰들에서 마지막 fit 키워드를 분리해 (경로, fit) 반환."""
    fit = default
    if tokens and tokens[-1].lower() in _FIT_VALUES:
        fit = tokens[-1].lower()
        tokens = tokens[:-1]
    return " ".join(tokens), fit


def _detect_kind(path: str) -> str:
    import os

    ext = os.path.splitext(path)[1].lower()
    return "video" if ext in _VIDEO_EXTS else "image"


def _parse_bg(args: List[str]) -> Background:
    if not args:
        raise ValueError("@bg 지시어에 스타일이 필요합니다 (color/gradient/image/video)")
    kind = args[0].lower()
    if kind == "color":
        return Background(kind="color", color=parse_color(args[1]))
    if kind == "gradient":
        return Background(
            kind="gradient",
            color=parse_color(args[1]),
            color2=parse_color(args[2]),
        )
    if kind in ("image", "video"):
        path, fit = _split_fit(args[1:])
        if not path:
            raise ValueError(f"@bg {kind} 에는 파일 경로가 필요합니다.")
        return Background(kind=kind, media_path=path, fit=fit)
    raise ValueError(f"알 수 없는 배경 스타일: {kind}")


def _parse_media(args: List[str]) -> Background:
    path, fit = _split_fit(args)
    if not path:
        raise ValueError("@media 에는 파일 경로가 필요합니다.")
    return Background(kind=_detect_kind(path), media_path=path, fit=fit)


def _parse_search(args: List[str]) -> Background:
    if not args:
        raise ValueError("@search 에는 검색어가 필요합니다.")
    media_type = "auto"
    if args[0].lower() in ("image", "video", "auto"):
        media_type = args[0].lower()
        args = args[1:]
    query = " ".join(args).strip()
    if not query:
        raise ValueError("@search 에는 검색어가 필요합니다.")
    return Background(kind="stock", query=query, media_type=media_type)


def _split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    out: List[str] = []
    for chunk in _SENTENCE_SPLIT.split(text):
        chunk = chunk.strip()
        if chunk:
            out.append(chunk)
    return out


def parse_script(text: str, default_background: Background) -> List[Scene]:
    """스크립트 문자열을 Scene 리스트로 변환."""
    # 빈 줄(공백만 있는 줄 포함) 기준으로 블록 분리.
    blocks = re.split(r"\n[ \t]*\n", text.strip("\n"))
    scenes: List[Scene] = []

    for block in blocks:
        lines = block.splitlines()
        if not any(line.strip() for line in lines):
            continue

        background: Optional[Background] = None
        title: Optional[str] = None
        voice: Optional[str] = None
        rate: Optional[str] = None
        fit: Optional[str] = None
        duration: Optional[float] = None
        narration_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("@"):
                parts = stripped[1:].split()
                if not parts:
                    continue
                key = parts[0].lower()
                rest = parts[1:]
                if key == "bg":
                    background = _parse_bg(rest)
                elif key == "media":
                    background = _parse_media(rest)
                elif key == "search":
                    background = _parse_search(rest)
                elif key == "fit":
                    if not rest or rest[0].lower() not in _FIT_VALUES:
                        raise ValueError("@fit 은 cover 또는 contain 이어야 합니다.")
                    fit = rest[0].lower()
                elif key == "title":
                    title = " ".join(rest)
                elif key == "duration":
                    duration = float(rest[0]) if rest else None
                elif key == "voice":
                    voice = rest[0] if rest else None
                elif key == "rate":
                    rate = rest[0] if rest else None
                else:
                    raise ValueError(f"알 수 없는 지시어: @{key}")
            else:
                narration_lines.append(stripped)

        segments: List[Segment] = []
        for line in narration_lines:
            for sentence in _split_sentences(line):
                segments.append(Segment(text=sentence))

        bg = background or default_background
        # @fit 은 배경에 덮어쓴다 (이미지/영상/스톡에만 의미 있음).
        if fit is not None:
            bg = Background(
                kind=bg.kind,
                color=bg.color,
                color2=bg.color2,
                media_path=bg.media_path,
                fit=fit,
                query=bg.query,
                media_type=bg.media_type,
            )

        # 본문도 제목도 미디어도 없는 빈 블록은 건너뜀.
        has_media = background is not None and background.kind in (
            "image",
            "video",
            "stock",
        )
        if not segments and not title and not has_media:
            continue

        scenes.append(
            Scene(
                background=bg,
                segments=segments,
                title=title,
                voice=voice,
                rate=rate,
                duration=duration,
            )
        )

    return scenes
