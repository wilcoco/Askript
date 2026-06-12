"""한글 자막 렌더링용 폰트 해석.

해석 순서:
  1) 명시적으로 지정한 경로 (--font / ASKRIPT_FONT)
  2) 시스템에 설치된 한글 폰트 (fc-match)
  3) 캐시 디렉터리에 받아둔 Noto Sans KR
  4) (인터넷) Noto Sans KR 자동 다운로드
"""

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional

# 한글이 깨지지 않는지 확인할 음절들.
_HANGUL_SAMPLES = "가나한글"

_CACHE_DIR = Path(
    os.environ.get("ASKRIPT_CACHE", Path.home() / ".cache" / "askript")
)
_FONT_URL = (
    "https://github.com/google/fonts/raw/main/ofl/notosanskr/"
    "NotoSansKR%5Bwght%5D.ttf"
)
_FONT_CACHE = _CACHE_DIR / "NotoSansKR.ttf"

# fc-match 로 찾아볼 후보 한글 폰트.
_SYSTEM_CANDIDATES = [
    "Noto Sans CJK KR",
    "Noto Sans KR",
    "NanumGothic",
    "Nanum Gothic",
    "Malgun Gothic",
    "AppleSDGothicNeo",
    "Source Han Sans KR",
]


def _covers_hangul(path: str) -> bool:
    try:
        from PIL import ImageFont

        font = ImageFont.truetype(path, 32)
        for ch in _HANGUL_SAMPLES:
            if font.getmask(ch).getbbox() is None:
                return False
        return True
    except Exception:
        return False


def _fc_match(name: str) -> Optional[str]:
    if not shutil.which("fc-match"):
        return None
    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{file}", name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        path = out.stdout.strip()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass
    return None


def _download_noto(insecure: bool = False) -> Optional[str]:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if insecure:
            import ssl

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=ctx)
            )
        else:
            opener = urllib.request.build_opener()
        with opener.open(_FONT_URL, timeout=60) as resp:
            data = resp.read()
        tmp = _FONT_CACHE.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(_FONT_CACHE)
        return str(_FONT_CACHE)
    except Exception:
        return None


def resolve_font(explicit: Optional[str] = None, insecure_download: bool = False) -> str:
    """사용할 한글 폰트 파일 경로를 반환.

    찾지 못하면 RuntimeError.
    """
    # 1) 명시적 지정
    candidate = explicit or os.environ.get("ASKRIPT_FONT")
    if candidate:
        if not os.path.exists(candidate):
            raise RuntimeError(f"지정한 폰트를 찾을 수 없습니다: {candidate}")
        return candidate

    # 2) 시스템 한글 폰트
    for name in _SYSTEM_CANDIDATES:
        path = _fc_match(name)
        if path and _covers_hangul(path):
            return path

    # 3) 캐시된 Noto
    if _FONT_CACHE.exists() and _covers_hangul(str(_FONT_CACHE)):
        return str(_FONT_CACHE)

    # 4) 자동 다운로드
    downloaded = _download_noto(insecure=insecure_download)
    if downloaded and _covers_hangul(downloaded):
        return downloaded

    raise RuntimeError(
        "한글 폰트를 찾을 수 없습니다. 다음 중 하나를 해주세요:\n"
        "  - 시스템에 한글 폰트 설치 (예: `apt install fonts-nanum`)\n"
        "  - --font 옵션으로 .ttf/.otf 경로 직접 지정\n"
        "  - 인터넷 연결 후 다시 실행 (Noto Sans KR 자동 다운로드)"
    )
