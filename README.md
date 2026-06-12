# Askript 🎬

**스크립트(대본)를 넣으면 유튜브용 동영상(mp4)으로 만들어 주는 프로그램입니다.**

텍스트 대본을 문장 단위로 나눠 **음성(TTS)** 으로 읽어주고, 화면에는 **자막**과
**배경**을 입혀 하나의 mp4 로 합성합니다.

```
대본(txt) ─▶ 문장 분리 ─▶ 음성 합성(Edge TTS) ─▶ 자막+배경 프레임 ─▶ ffmpeg ─▶ video.mp4
```

미리보기 예시(자막/배경):

| 그라데이션 배경 | 단색 배경 |
|---|---|
| 상단 제목 + 하단 자막 | 장면마다 배경 변경 가능 |

---

## 설치

```bash
pip install -r requirements.txt
# 또는 패키지로 설치
pip install -e .
```

- **ffmpeg** 는 `imageio-ffmpeg` 가 자동으로 번들 바이너리를 제공하므로 별도 설치가
  필요 없습니다. (시스템 ffmpeg 가 있으면 그것도 사용 가능)
- **한글 폰트** 가 시스템에 없으면 처음 실행할 때 Noto Sans KR 을 자동으로
  내려받습니다. 직접 지정하려면 `--font /경로/폰트.ttf`.

## 사용법

```bash
# 가장 기본 (Edge TTS 음성 + 그라데이션 배경)
python -m askript examples/sample_script.txt -o video.mp4

# 인터넷 없이 타이밍/자막만 미리보기 (무음)
python -m askript examples/sample_script.txt --tts silent -o preview.mp4

# 배경 스타일 선택
python -m askript script.txt --style color --bg-color "#101418"
python -m askript script.txt --style gradient --gradient "#001027" "#0a3d91"
python -m askript script.txt --style image --bg-image bg.png

# 목소리 / 속도 / 해상도
python -m askript script.txt --voice ko-KR-InJoonNeural --rate "+10%"
python -m askript script.txt --resolution shorts   # 세로 영상(쇼츠)

# 자주 쓰는 목소리 보기
python -m askript --list-voices
```

> `--style` 은 **기본** 배경이고, 대본 안의 `@bg` 지시어가 장면별로 우선합니다.
> 그래서 "그때그때" 장면마다 다른 배경을 줄 수 있습니다.

## 대본 형식

UTF-8 텍스트 파일입니다.

- **빈 줄**로 장면(scene)을 구분합니다.
- `@` 로 시작하는 줄은 그 장면의 **지시어**입니다.
- 나머지 줄은 내레이션 본문이며, **문장 단위**로 음성·자막이 됩니다.

| 지시어 | 설명 |
|---|---|
| `@bg color #1e2a44` | 단색 배경 |
| `@bg gradient #001027 #0a3d91` | 위→아래 그라데이션 |
| `@bg image path/to.png` | 이미지 배경(화면에 꽉 차게) |
| `@title 화면 상단 제목` | 장면 제목(상단 표시) |
| `@voice ko-KR-InJoonNeural` | 이 장면만 다른 목소리 |
| `@rate +10%` | 이 장면만 말하기 속도 |

예시 (`examples/sample_script.txt`):

```
@bg gradient #001027 #0a3d91
@title 오늘의 주제
안녕하세요. 오늘은 인공지능에 대해 이야기합니다.
인공지능은 우리 삶을 빠르게 바꾸고 있습니다.

@bg color #101418
@title 두 번째 장면
배경이 단색으로 바뀌었습니다.
```

## 옵션 요약

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `-o, --out` | `output.mp4` | 출력 파일 |
| `--style` | `gradient` | 기본 배경 (color/gradient/image) |
| `--bg-color` | `#101418` | 단색 색상 |
| `--gradient` | `#001027 #0a3d91` | 그라데이션 두 색 |
| `--bg-image` | – | 이미지 배경 경로 |
| `--tts` | `edge` | `edge`(실음성) / `silent`(무음 미리보기) |
| `--voice` | `ko-KR-SunHiNeural` | Edge TTS 목소리 |
| `--rate` | `+0%` | 말하기 속도 |
| `--resolution` | `1080p` | `1080p`/`720p`/`480p`/`shorts`(세로) |
| `--fps` | `30` | 프레임레이트 |
| `--font` | 자동 | 자막 폰트(.ttf/.otf) |

## 구조

```
askript/
  cli.py        명령줄 인터페이스
  parser.py     대본 → 장면/문장 파싱
  tts.py        음성 합성 (edge / silent)
  visuals.py    배경 생성 + 자막 프레임 합성 (Pillow)
  render.py     전체 파이프라인 (프레임+음성 → ffmpeg → mp4)
  ffmpeg.py     ffmpeg 실행/길이 측정 헬퍼
  fonts.py      한글 폰트 자동 해석/다운로드
```

## 한계 / 다음 단계

현재는 **MVP** 입니다. 확장하기 좋은 부분:

- 🎥 스톡 영상 배경(Pexels 등) / AI 생성 이미지 배경
- 🎵 배경 음악(BGM) 믹싱
- 🗣️ 단어 단위 자막 싱크(노래방 스타일)
- ⬆️ YouTube Data API 자동 업로드

## 라이선스

코드는 자유롭게 사용하세요. 자동 다운로드되는 Noto Sans KR 폰트는
[SIL Open Font License](https://github.com/google/fonts/tree/main/ofl/notosanskr) 를 따릅니다.
