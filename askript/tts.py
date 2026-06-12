"""음성 합성(TTS) 백엔드.

backend:
  "edge"   : Microsoft Edge TTS (무료, 고품질). 단, 클라우드/데이터센터 IP 에서는
             마이크로소프트가 차단해 실패할 수 있다(NoAudioReceived).
  "gtts"   : Google TTS (무료). 한 가지 목소리뿐이지만 서버 환경에서 잘 동작한다.
  "auto"   : edge 를 먼저 시도하고 실패하면 gtts 로 자동 대체 (render 에서 처리).
  "silent" : 무음 오디오 (인터넷 없이 자막/타이밍 미리보기용).
"""

from __future__ import annotations

import asyncio
import os
import time

from . import ffmpeg

# 무음 백엔드에서 글자 수로 길이를 추정할 때 쓰는 값 (대략 한국어 발화 속도).
_CHARS_PER_SEC = 5.5
_MIN_DURATION = 1.2
_TAIL_PAD = 0.4  # 문장 끝 약간의 여백.


def estimate_duration(text: str) -> float:
    return max(_MIN_DURATION, len(text) / _CHARS_PER_SEC + _TAIL_PAD)


async def _stream_edge(text: str, voice: str, rate: str, out_path: str) -> bool:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    got_audio = False
    with open(out_path, "wb") as fh:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                got_audio = True
                fh.write(chunk["data"])
    return got_audio


def _synth_edge(text: str, voice: str, rate: str, out_path: str, retries: int = 2) -> None:
    """Edge TTS 합성. 실패 시 몇 번 재시도 후 예외."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            got = asyncio.run(_stream_edge(text, voice, rate, out_path))
            if got and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return
            last_err = RuntimeError("Edge TTS 가 오디오를 반환하지 않았습니다.")
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"Edge TTS 실패: {last_err}")


def _synth_gtts(text: str, out_path: str) -> None:
    from gtts import gTTS

    gTTS(text=text, lang="ko").save(out_path)
    if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
        raise RuntimeError("gTTS 가 오디오를 생성하지 못했습니다.")


def synthesize(
    text: str,
    out_path: str,
    backend: str = "edge",
    voice: str = "ko-KR-SunHiNeural",
    rate: str = "+0%",
) -> float:
    """text 를 음성으로 합성해 out_path(mp3) 에 저장하고 길이(초)를 반환.

    'auto' 는 render 단계에서 edge->gtts 로 처리하므로 여기서는 edge 로 취급한다.
    """
    if backend == "silent":
        duration = estimate_duration(text)
        ffmpeg.make_silence(out_path, duration)
        return duration

    if backend == "gtts":
        _synth_gtts(text, out_path)
        return ffmpeg.probe_duration(out_path)

    if backend in ("edge", "auto"):
        _synth_edge(text, voice, rate, out_path)
        return ffmpeg.probe_duration(out_path)

    raise ValueError(f"알 수 없는 TTS 백엔드: {backend}")
