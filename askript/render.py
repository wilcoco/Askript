"""전체 파이프라인: 스크립트 -> mp4."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import ffmpeg, media, tts, visuals
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
    pexels_key: Optional[str] = None
    insecure_download: bool = False


def _encode_static_segment(
    frame_png: str,
    audio_mp3: str,
    duration: float,
    out_mp4: str,
    size: Tuple[int, int],
    fps: int,
) -> None:
    """정지 화면(색/그라데이션/이미지) 1장 + 음성 -> 클립."""
    w, h = size
    ffmpeg.run(
        [
            "-loop", "1",
            "-i", frame_png,
            "-i", audio_mp3,
            "-t", f"{duration:.3f}",
            "-vf", f"scale={w}:{h},format=yuv420p",
            "-r", str(fps),
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            out_mp4,
        ]
    )


def _encode_video_segment(
    video_path: str,
    offset: float,
    overlay_png: str,
    audio_mp3: str,
    duration: float,
    out_mp4: str,
    size: Tuple[int, int],
    fps: int,
    fit: str,
) -> None:
    """동영상 배경에 자막 오버레이를 얹은 클립.

    offset 만큼 영상 안에서 이어 재생하고(장면 내 연속 재생), 영상이 짧으면
    -stream_loop 로 반복한다.
    """
    w, h = size
    if fit == "contain":
        scale = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        )
    else:
        scale = (
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1"
        )
    filter_complex = f"[0:v]{scale},fps={fps}[bg];[bg][1:v]overlay=0:0[v]"
    ffmpeg.run(
        [
            "-stream_loop", "-1", "-ss", f"{offset:.3f}", "-i", video_path,
            "-loop", "1", "-i", overlay_png,
            "-i", audio_mp3,
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "2:a",
            "-t", f"{duration:.3f}",
            "-r", str(fps),
            "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-pix_fmt", "yuv420p",
            out_mp4,
        ]
    )


def _concat(segment_paths: List[str], out_path: str, workdir: str) -> None:
    list_file = os.path.join(workdir, "concat.txt")
    with open(list_file, "w", encoding="utf-8") as fh:
        for path in segment_paths:
            safe = path.replace("'", "'\\''")
            fh.write(f"file '{safe}'\n")
    ffmpeg.run(
        ["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out_path]
    )


def render_scenes(scenes: List[Scene], options: RenderOptions, progress=None) -> str:
    """Scene 리스트를 mp4 로 렌더링하고 결과 경로를 반환."""
    if not scenes:
        raise ValueError("렌더링할 장면이 없습니다. 스크립트가 비어 있나요?")

    portrait = options.size[1] > options.size[0]
    total = sum(max(1, len(s.segments)) for s in scenes)
    workdir = tempfile.mkdtemp(prefix="askript_")
    segment_paths: List[str] = []
    # 배경별 캐시: id(background) -> (media_path, is_video, video_duration, base_image)
    resolved: Dict[int, Tuple[Optional[str], bool, float, object]] = {}
    counter = 0

    try:
        for scene in scenes:
            bg = scene.background
            key = id(bg)
            if key not in resolved:
                mpath, is_video = media.resolve_media(
                    bg,
                    api_key=options.pexels_key,
                    portrait=portrait,
                    insecure=options.insecure_download,
                )
                vdur = ffmpeg.probe_duration(mpath) if is_video and mpath else 0.0
                base_img = (
                    None
                    if is_video
                    else visuals.make_background(bg, options.size, image_path=mpath)
                )
                resolved[key] = (mpath, is_video, vdur, base_img)
            mpath, is_video, vdur, base_img = resolved[key]

            # 이 장면의 (자막, ) 단위 목록. 본문이 없으면 b-roll 한 컷.
            seg_texts: List[str] = [s.text for s in scene.segments] or [""]
            scene_offset = 0.0  # 동영상 배경의 장면 내 재생 위치.

            for seg_idx, text in enumerate(seg_texts):
                counter += 1
                if progress:
                    progress(counter, total, text or "(미디어)")

                # 오디오
                audio_mp3 = os.path.join(workdir, f"audio_{counter:04d}.mp3")
                if text:
                    duration = tts.synthesize(
                        text,
                        audio_mp3,
                        backend=options.tts_backend,
                        voice=scene.voice or options.voice,
                        rate=scene.rate or options.rate,
                    )
                else:
                    # b-roll: @duration, 영상 길이, 기본 4초 순으로 결정.
                    duration = scene.duration or (vdur if is_video and vdur else 4.0)
                    ffmpeg.make_silence(audio_mp3, duration)

                seg_mp4 = os.path.join(workdir, f"seg_{counter:04d}.mp4")
                if is_video:
                    overlay = visuals.render_overlay(
                        options.size,
                        options.font_path,
                        subtitle=text or None,
                        title=scene.title,
                    )
                    overlay_png = os.path.join(workdir, f"ov_{counter:04d}.png")
                    overlay.save(overlay_png)
                    off = (scene_offset % vdur) if vdur else 0.0
                    _encode_video_segment(
                        mpath, off, overlay_png, audio_mp3, duration,
                        seg_mp4, options.size, options.fps, bg.fit,
                    )
                    scene_offset += duration
                else:
                    frame = visuals.compose_frame(
                        base_img,
                        options.font_path,
                        subtitle=text or None,
                        title=scene.title,
                    )
                    frame_png = os.path.join(workdir, f"frame_{counter:04d}.png")
                    frame.save(frame_png)
                    _encode_static_segment(
                        frame_png, audio_mp3, duration,
                        seg_mp4, options.size, options.fps,
                    )
                segment_paths.append(seg_mp4)

        _concat(segment_paths, options.out_path, workdir)
        return options.out_path
    finally:
        if options.keep_temp:
            print(f"[임시 파일 보존] {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
