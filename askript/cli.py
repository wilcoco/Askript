"""명령줄 인터페이스."""

from __future__ import annotations

import argparse
import sys
from typing import List

from . import __version__, fonts
from .models import Background
from .parser import parse_color, parse_script
from .render import RenderOptions, render_scenes

# 자주 쓰는 한국어 목소리 (참고용).
COMMON_VOICES = [
    "ko-KR-SunHiNeural",   # 여성
    "ko-KR-InJoonNeural",  # 남성
    "ko-KR-HyunsuMultilingualNeural",
]

RESOLUTIONS = {
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "480p": (854, 480),
    "shorts": (1080, 1920),  # 세로 (유튜브 쇼츠)
}


def _default_background(args) -> Background:
    style = args.style
    if style == "color":
        return Background(kind="color", color=parse_color(args.bg_color))
    if style == "gradient":
        c1, c2 = args.gradient
        return Background(
            kind="gradient", color=parse_color(c1), color2=parse_color(c2)
        )
    if style == "image":
        if not args.bg_image:
            raise SystemExit("--style image 에는 --bg-image 경로가 필요합니다.")
        return Background(kind="image", image_path=args.bg_image)
    raise SystemExit(f"알 수 없는 스타일: {style}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="askript",
        description="스크립트(대본)를 유튜브용 mp4 동영상으로 만듭니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "예시:\n"
            "  python -m askript script.txt -o video.mp4\n"
            "  python -m askript script.txt --style gradient "
            "--gradient '#001027' '#0a3d91'\n"
            "  python -m askript script.txt --style image --bg-image bg.png\n"
            "  python -m askript script.txt --tts silent   # 인터넷 없이 미리보기\n"
        ),
    )
    p.add_argument(
        "script",
        nargs="?",
        help="스크립트 텍스트 파일 경로 ('-' 는 표준입력)",
    )
    p.add_argument("-o", "--out", default="output.mp4", help="출력 mp4 경로")

    # 비주얼(배경) 기본값 — 장면 안의 @bg 지시어가 우선합니다.
    p.add_argument(
        "--style",
        choices=["color", "gradient", "image"],
        default="gradient",
        help="기본 배경 스타일 (기본: gradient)",
    )
    p.add_argument("--bg-color", default="#101418", help="단색 배경 색 (#RRGGBB)")
    p.add_argument(
        "--gradient",
        nargs=2,
        metavar=("TOP", "BOTTOM"),
        default=["#001027", "#0a3d91"],
        help="그라데이션 두 색",
    )
    p.add_argument("--bg-image", help="이미지 배경 파일 경로")

    # 음성
    p.add_argument(
        "--tts",
        dest="tts_backend",
        choices=["edge", "silent"],
        default="edge",
        help="TTS 백엔드 (기본: edge / silent=무음 미리보기)",
    )
    p.add_argument(
        "--voice",
        default="ko-KR-SunHiNeural",
        help="Edge TTS 목소리 (예: ko-KR-InJoonNeural)",
    )
    p.add_argument("--rate", default="+0%", help="말하기 속도 (예: +10%%, -10%%)")

    # 영상
    p.add_argument(
        "--resolution",
        choices=list(RESOLUTIONS),
        default="1080p",
        help="해상도 (기본: 1080p, shorts=세로)",
    )
    p.add_argument("--fps", type=int, default=30, help="프레임레이트 (기본: 30)")
    p.add_argument("--font", help="자막용 폰트 파일(.ttf/.otf) 경로")

    p.add_argument(
        "--insecure-font-download",
        action="store_true",
        help="폰트 자동 다운로드 시 SSL 검증 비활성화 (프록시 환경용)",
    )
    p.add_argument("--keep-temp", action="store_true", help="임시 파일 보존")
    p.add_argument(
        "--list-voices", action="store_true", help="자주 쓰는 한국어 목소리 출력"
    )
    p.add_argument("--version", action="version", version=f"askript {__version__}")
    return p


def main(argv: List[str] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_voices:
        print("자주 쓰는 한국어 Edge TTS 목소리:")
        for v in COMMON_VOICES:
            print("  -", v)
        print("\n전체 목록: `edge-tts --list-voices | grep ko-KR`")
        return 0

    if not args.script:
        print("스크립트 파일 경로가 필요합니다. (-h 로 도움말)", file=sys.stderr)
        return 1

    # 스크립트 읽기
    if args.script == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(args.script, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            print(f"스크립트를 읽을 수 없습니다: {e}", file=sys.stderr)
            return 1

    try:
        default_bg = _default_background(args)
        scenes = parse_script(text, default_bg)
    except ValueError as e:
        print(f"스크립트 파싱 오류: {e}", file=sys.stderr)
        return 1

    if not scenes:
        print("스크립트에서 장면을 찾지 못했습니다.", file=sys.stderr)
        return 1

    try:
        font_path = fonts.resolve_font(
            args.font, insecure_download=args.insecure_font_download
        )
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    options = RenderOptions(
        out_path=args.out,
        size=RESOLUTIONS[args.resolution],
        fps=args.fps,
        font_path=font_path,
        tts_backend=args.tts_backend,
        voice=args.voice,
        rate=args.rate,
        keep_temp=args.keep_temp,
    )

    n_segments = sum(max(1, len(s.segments)) for s in scenes)
    print(
        f"장면 {len(scenes)}개 · 자막 {n_segments}개 · "
        f"{args.resolution} · TTS={args.tts_backend} · 폰트={font_path}"
    )

    def progress(i, total, text):
        preview = (text[:24] + "…") if len(text) > 24 else text
        print(f"  [{i}/{total}] {preview}")

    try:
        out = render_scenes(scenes, options, progress=progress)
    except Exception as e:
        print(f"렌더링 실패: {e}", file=sys.stderr)
        return 1

    print(f"\n완료 ✅  → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
