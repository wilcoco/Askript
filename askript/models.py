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
        "image"    : 로컬 이미지 파일 (media_path)
        "video"    : 로컬 동영상 파일 (media_path)
        "stock"    : 키워드 검색으로 받아온 스톡 이미지/영상 (query)

    fit:
        "cover"   : 화면에 꽉 차게 (넘치는 부분은 잘림)
        "contain" : 잘리지 않게 전체를 보이고 여백은 채움 (다이어그램/스크린샷용)
    """

    kind: str = "color"
    color: RGB = (18, 22, 33)
    color2: Optional[RGB] = None
    media_path: Optional[str] = None
    fit: str = "cover"

    # 스톡 검색용 (kind == "stock")
    query: Optional[str] = None
    media_type: str = "auto"  # image | video | auto


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
    duration: Optional[float] = None  # 내레이션 없는 b-roll 장면의 길이(초)
