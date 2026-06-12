"""전체 파이프라인: 스크립트 -> mp4."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import ffmpeg, tts, visuals
from .models import Scene


@dataclass
class RenderOptions:
    out_path: str = "output.mp4"
    size: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    font_path: str = ""
    tts_backend: str = "edge"
    voice: str = "ko-KR-SunHiNeural"
    rate: str = "+0%"
    keep_temp: bool = False


def _encode_segment(
    frame_png: str,
    audio_mp3: str,
    duration: float,
    out_mp4: str,
    size: Tuple[int, int],
    fps: int,
) -> None:
    w, h = size
    ffmpeg.run(
        [
            "-loop", "1",
            "-i", frame_png,
            "-i", audio_mp3,
            "-t", f"{duration:.3f}",
            "-vf", f"scale={w}:{h},format=yuv420p",
            "-r", str(fps),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            out_mp4,
        ]
    )


def _concat(segment_paths: List[str], out_path: str, workdir: str) -> None:
    list_file = os.path.join(workdir, "concat.txt")
    with open(list_file, "w", encoding="utf-8") as fh:
        for path in segment_paths:
            # ffmpeg concat 데모서: 경로의 작은따옴표 이스케이프.
            safe = path.replace("'", "'\\''")
            fh.write(f"file '{safe}'\n")
    ffmpeg.run(
        ["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out_path]
    )


def render_scenes(
    scenes: List[Scene],
    options: RenderOptions,
    progress=None,
) -> str:
    """Scene 리스트를 mp4 로 렌더링하고 결과 경로를 반환."""
    if not scenes:
        raise ValueError("렌더링할 장면이 없습니다. 스크립트가 비어 있나요?")

    # (scene, segment) 단위로 펼친다.
    units: List[Tuple[Scene, Optional[object]]] = []
    for scene in scenes:
        if scene.segments:
            for seg in scene.segments:
                units.append((scene, seg))
        else:
            # 본문 없이 제목만 있는 장면 -> 짧은 타이틀 카드.
            units.append((scene, None))

    total = len(units)
    workdir = tempfile.mkdtemp(prefix="askript_")
    segment_paths: List[str] = []
    bg_cache: dict = {}

    try:
        for idx, (scene, seg) in enumerate(units):
            text = seg.text if seg is not None else ""
            if progress:
                progress(idx + 1, total, text)

            # 배경 이미지 (장면별 캐시)
            key = id(scene.background)
            if key not in bg_cache:
                bg_cache[key] = visuals.make_background(
                    scene.background, options.size
                )
            background = bg_cache[key]

            # 프레임
            frame = visuals.compose_frame(
                background,
                options.font_path,
                subtitle=text or None,
                title=scene.title,
            )
            frame_png = os.path.join(workdir, f"frame_{idx:04d}.png")
            frame.save(frame_png)

            # 오디오
            audio_mp3 = os.path.join(workdir, f"audio_{idx:04d}.mp3")
            if text:
                duration = tts.synthesize(
                    text,
                    audio_mp3,
                    backend=options.tts_backend,
                    voice=scene.voice or options.voice,
                    rate=scene.rate or options.rate,
                )
            else:
                # 타이틀 카드: 2초 무음.
                duration = 2.0
                ffmpeg.make_silence(audio_mp3, duration)

            seg_mp4 = os.path.join(workdir, f"seg_{idx:04d}.mp4")
            _encode_segment(
                frame_png, audio_mp3, duration, seg_mp4, options.size, options.fps
            )
            segment_paths.append(seg_mp4)

        _concat(segment_paths, options.out_path, workdir)
        return options.out_path
    finally:
        if not options.keep_temp:
            import shutil

            shutil.rmtree(workdir, ignore_errors=True)
        else:
            print(f"[임시 파일 보존] {workdir}")
