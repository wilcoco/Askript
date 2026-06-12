"""스톡 미디어 검색/다운로드 (Pexels) 및 배경 미디어 해석.

`@search 키워드` 로 지정한 장면은 여기서 Pexels API 로 검색해 이미지/영상을
내려받아 로컬 파일 경로로 바꿔준다.

API 키:
    - 환경변수 PEXELS_API_KEY  (권장)
    - 또는 CLI --pexels-key
    - https://www.pexels.com/api/ 에서 무료 발급
"""

from __future__ import annotations

import hashlib
import json
import os
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from .models import Background

_CACHE_DIR = Path(
    os.environ.get("ASKRIPT_CACHE", Path.home() / ".cache" / "askript")
) / "stock"

_PEXELS_IMG = "https://api.pexels.com/v1/search"
_PEXELS_VID = "https://api.pexels.com/videos/search"


class StockError(RuntimeError):
    pass


def _http_get(url: str, headers: dict, insecure: bool) -> bytes:
    ctx = None
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        return resp.read()


def _cache_path(prefix: str, key: str, ext: str) -> Path:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return _CACHE_DIR / f"{prefix}_{digest}{ext}"


def _download(url: str, dest: Path, insecure: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = _http_get(url, headers={}, insecure=insecure)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(dest)


def _search_image(query: str, key: str, orientation: str, insecure: bool) -> str:
    params = urllib.parse.urlencode(
        {"query": query, "per_page": 1, "orientation": orientation}
    )
    raw = _http_get(
        f"{_PEXELS_IMG}?{params}",
        headers={"Authorization": key},
        insecure=insecure,
    )
    data = json.loads(raw)
    photos = data.get("photos") or []
    if not photos:
        raise StockError(f"'{query}' 에 대한 이미지 검색 결과가 없습니다.")
    src = photos[0]["src"]
    return src.get("large2x") or src.get("large") or src.get("original")


def _search_video(query: str, key: str, orientation: str, insecure: bool) -> str:
    params = urllib.parse.urlencode(
        {"query": query, "per_page": 1, "orientation": orientation}
    )
    raw = _http_get(
        f"{_PEXELS_VID}?{params}",
        headers={"Authorization": key},
        insecure=insecure,
    )
    data = json.loads(raw)
    videos = data.get("videos") or []
    if not videos:
        raise StockError(f"'{query}' 에 대한 동영상 검색 결과가 없습니다.")
    files = videos[0].get("video_files", [])
    # mp4 중 너비 1920 이하에서 가장 큰 것을 고른다 (없으면 첫 번째).
    mp4s = [f for f in files if f.get("file_type") == "video/mp4"]
    mp4s.sort(key=lambda f: (f.get("width") or 0))
    pick = None
    for f in mp4s:
        if (f.get("width") or 0) <= 1920:
            pick = f
    pick = pick or (mp4s[-1] if mp4s else (files[0] if files else None))
    if not pick:
        raise StockError(f"'{query}' 동영상의 다운로드 링크를 찾지 못했습니다.")
    return pick["link"]


def resolve_stock(
    bg: Background,
    api_key: Optional[str],
    portrait: bool = False,
    insecure: bool = False,
) -> Tuple[str, bool]:
    """스톡 배경을 (로컬경로, is_video) 로 해석. 검색·다운로드·캐시 포함."""
    key = api_key or os.environ.get("PEXELS_API_KEY")
    if not key:
        raise StockError(
            "스톡 검색에는 Pexels API 키가 필요합니다. "
            "환경변수 PEXELS_API_KEY 를 설정하거나 --pexels-key 로 전달하세요. "
            "(무료 발급: https://www.pexels.com/api/)"
        )

    orientation = "portrait" if portrait else "landscape"
    want = bg.media_type
    query = bg.query or ""

    # auto 이거나 video 면 영상 우선 시도, image 면 이미지.
    order = []
    if want == "image":
        order = ["image"]
    elif want == "video":
        order = ["video"]
    else:  # auto: 영상 먼저, 없으면 이미지
        order = ["video", "image"]

    last_err: Optional[Exception] = None
    for kind in order:
        try:
            if kind == "image":
                url = _search_image(query, key, orientation, insecure)
                dest = _cache_path("img", f"{query}|{orientation}", ".jpg")
                if not dest.exists():
                    _download(url, dest, insecure)
                return str(dest), False
            else:
                url = _search_video(query, key, orientation, insecure)
                dest = _cache_path("vid", f"{query}|{orientation}", ".mp4")
                if not dest.exists():
                    _download(url, dest, insecure)
                return str(dest), True
        except StockError as e:
            last_err = e
            continue
    raise last_err or StockError(f"'{query}' 검색 실패")


def resolve_media(bg: Background, **stock_kwargs) -> Tuple[Optional[str], bool]:
    """배경의 미디어를 (로컬경로, is_video) 로 해석.

    color/gradient 는 (None, False) 를 반환.
    """
    if bg.kind in ("color", "gradient"):
        return None, False
    if bg.kind == "image":
        return bg.media_path, False
    if bg.kind == "video":
        return bg.media_path, True
    if bg.kind == "stock":
        return resolve_stock(bg, **stock_kwargs)
    raise ValueError(f"알 수 없는 배경 종류: {bg.kind}")
