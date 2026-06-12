"""데이터 모델 정의."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

RGB = Tuple[int, int, int]


@dataclass
class Background:
    """장면 배경 스타일.

    kind:
        "color"    : 단색 (color)
        "gradient" : 위->아래 그라데이션 (color -> color2)
        "image"    : 이미지 파일 (image_path 를 화면에 꽉 차게)
    """

    kind: str = "color"
    color: RGB = (18, 22, 33)
    color2: Optional[RGB] = None
    image_path: Optional[str] = None


@dataclass
class Segment:
    """하나의 자막/음성 단위 (보통 한 문장)."""

    text: str


@dataclass
class Scene:
    """배경 하나를 공유하는 장면."""

    background: Background
    segments: List[Segment] = field(default_factory=list)
    title: Optional[str] = None
    voice: Optional[str] = None
    rate: Optional[str] = None
