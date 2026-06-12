"""ffmpeg 실행 헬퍼."""

from __future__ import annotations

import re
import shutil
import subprocess
from functools import lru_cache
from typing import List


@lru_cache(maxsize=1)
def ffmpeg_path() -> str:
    """사용할 ffmpeg 실행 파일 경로.

    1) imageio-ffmpeg 번들 바이너리 (설치만 하면 별도 ffmpeg 불필요)
    2) 시스템 PATH 의 ffmpeg
    """
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    system = shutil.which("ffmpeg")
    if system:
        return system
    raise RuntimeError(
        "ffmpeg 를 찾을 수 없습니다. `pip install imageio-ffmpeg` 또는 "
        "시스템에 ffmpeg 를 설치하세요."
    )


def run(args: List[str]) -> subprocess.CompletedProcess:
    """ffmpeg <args> 실행. 실패 시 stderr 와 함께 예외."""
    cmd = [ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "ffmpeg 실행 실패:\n  명령: %s\n  오류: %s"
            % (" ".join(cmd), proc.stderr.strip())
        )
    return proc


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)")


def probe_duration(path: str) -> float:
    """미디어 파일의 길이(초)를 반환. (ffprobe 없이 ffmpeg 만으로)"""
    proc = subprocess.run(
        [ffmpeg_path(), "-hide_banner", "-i", path],
        capture_output=True,
        text=True,
    )
    # ffmpeg 는 -i 만 주면 "오류"로 끝나지만 stderr 에 Duration 을 출력한다.
    match = _DURATION_RE.search(proc.stderr)
    if not match:
        raise RuntimeError(f"길이를 알 수 없습니다: {path}\n{proc.stderr}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def make_silence(out_path: str, duration: float) -> None:
    """무음 mp3 생성 (TTS 없이 타이밍만 미리보기할 때 사용)."""
    run(
        [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            f"{duration:.3f}",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "9",
            out_path,
        ]
    )
