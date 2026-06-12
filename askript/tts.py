"""음성 합성(TTS) 백엔드.

backend:
  "edge"   : Microsoft Edge TTS (무료, 고품질, 인터넷 필요)
  "silent" : 무음 오디오 (인터넷 없이 자막/타이밍 미리보기용)
"""

from __future__ import annotations

import asyncio

from . import ffmpeg

# 무음 백엔드에서 글자 수로 길이를 추정할 때 쓰는 값 (대략 한국어 발화 속도).
_CHARS_PER_SEC = 5.5
_MIN_DURATION = 1.2
_TAIL_PAD = 0.4  # 문장 끝 약간의 여백.


def estimate_duration(text: str) -> float:
    return max(_MIN_DURATION, len(text) / _CHARS_PER_SEC + _TAIL_PAD)


async def _synth_edge(text: str, voice: str, rate: str, out_path: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    with open(out_path, "wb") as fh:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])


def synthesize(
    text: str,
    out_path: str,
    backend: str = "edge",
    voice: str = "ko-KR-SunHiNeural",
    rate: str = "+0%",
) -> float:
    """text 를 음성으로 합성해 out_path(mp3) 에 저장하고 길이(초)를 반환."""
    if backend == "silent":
        duration = estimate_duration(text)
        ffmpeg.make_silence(out_path, duration)
        return duration

    if backend == "edge":
        asyncio.run(_synth_edge(text, voice, rate, out_path))
        return ffmpeg.probe_duration(out_path)

    raise ValueError(f"알 수 없는 TTS 백엔드: {backend}")
