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

## 웹앱으로 쓰기 (브라우저)

대본을 붙여넣고 버튼만 누르면 영상이 나오는 **웹 인터페이스**가 들어 있습니다.

```bash
pip install -r requirements.txt
uvicorn webapp:app --reload
# 브라우저에서 http://127.0.0.1:8000 접속
```

### Railway 로 배포 (깃 푸시 → 자동 웹 배포)

이 저장소에는 `Dockerfile` 과 `railway.toml` 이 있어 **Railway 에 그대로 배포**됩니다.

1. [railway.app](https://railway.app) 에서 **New Project → Deploy from GitHub repo** 로 이 저장소 선택
2. Railway 가 `Dockerfile` 로 자동 빌드 → 공개 URL 생성 (이후 깃에 푸시할 때마다 자동 재배포)
3. (선택) **Variables** 에 `PEXELS_API_KEY` 를 넣으면 `@search` 를 매번 키 입력 없이 사용
4. 생성된 URL 로 접속해 브라우저에서 영상 생성

> 음성(Edge TTS)은 인터넷이 열린 Railway 서버에서 정상 동작하므로, **웹에서 바로
> 음성이 들어간 영상**을 만들 수 있습니다. 단, 웹 버전에서는 서버에 없는 로컬 파일
> (`@bg image 내파일.png`)은 못 쓰니 미디어는 `@search` 로 넣으세요.

## 설치 (명령줄로 쓰기)

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
| `@bg image bg.png [cover\|contain]` | 로컬 이미지 배경 |
| `@bg video clip.mp4 [cover\|contain]` | 로컬 동영상 배경(자막이 위에 얹힘) |
| `@media path [fit]` | 이미지/동영상 자동 감지 |
| `@search [image\|video] 키워드` | 스톡(Pexels)에서 검색해 배경으로 사용 |
| `@fit cover\|contain` | 화면맞춤(꽉채움/잘림없이) |
| `@title 화면 상단 제목` | 장면 제목(상단 표시) |
| `@duration 5` | 내레이션 없는 b-roll 장면 길이(초) |
| `@voice ko-KR-InJoonNeural` | 이 장면만 다른 목소리 |
| `@rate +10%` | 이 장면만 말하기 속도 |

### 이미지·동영상 넣기 (원하는 지점에)

장면(빈 줄로 구분)마다 배경을 따로 줄 수 있으므로, **넣고 싶은 지점에서 새 장면을
시작**하면 됩니다. 동영상은 그 장면 동안 재생되고, 문장이 여러 개여도 끊기지 않고
이어집니다.

```
여기까지는 그라데이션 배경으로 설명합니다.

@bg video assets/ocean.mp4
@title 바다
이 부분에서는 바다 영상이 흐릅니다.
영상은 멈추지 않고 계속 재생됩니다.

@media diagram.png contain
@title 구조도
다이어그램은 잘리지 않게 통째로 보여줍니다.
```

> 다이어그램·스크린샷처럼 **잘리면 안 되는** 자료는 `contain`,
> 풍경·배경처럼 **꽉 채우고 싶은** 영상은 `cover`(기본)를 쓰세요.

### 키워드로 검색해서 넣기 (스톡 영상/이미지)

`@search` 를 쓰면 [Pexels](https://www.pexels.com/api/) 무료 스톡에서 키워드로
이미지·영상을 자동으로 받아 배경으로 씁니다. **무료 API 키**가 필요합니다.

```bash
# 1) https://www.pexels.com/api/ 에서 무료 키 발급
# 2) 환경변수로 등록 (권장)
export PEXELS_API_KEY="여기에_발급받은_키"
# 또는 실행할 때: --pexels-key "키"
```

```
@search video 우주 은하수
오늘은 우주에 대해 이야기합니다.

@search image 인공지능
인공지능은 빠르게 발전하고 있습니다.
```

- `@search 키워드` (타입 생략) → 영상을 먼저 찾고 없으면 이미지.
- 받은 파일은 `~/.cache/askript/stock/` 에 캐시되어 다음엔 다시 받지 않습니다.

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
| `--fit` | `cover` | 이미지/영상 화면맞춤 기본값 (cover/contain) |
| `--pexels-key` | – | Pexels API 키(`@search` 용, 환경변수로도 가능) |
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
  visuals.py    배경 생성 + 자막 프레임/오버레이 합성 (Pillow)
  media.py      스톡(Pexels) 검색·다운로드 + 배경 미디어 해석
  render.py     전체 파이프라인 (정지화면/동영상 + 음성 → ffmpeg → mp4)
  ffmpeg.py     ffmpeg 실행/길이 측정 헬퍼
  fonts.py      한글 폰트 자동 해석/다운로드
webapp.py       웹 인터페이스 (FastAPI) — 브라우저에서 영상 생성
Dockerfile      배포용 컨테이너 (Railway 등)
railway.toml    Railway 배포 설정
```

## 한계 / 다음 단계

확장하기 좋은 부분:

- 🎵 배경 음악(BGM) 믹싱
- 🗣️ 단어 단위 자막 싱크(노래방 스타일)
- 🖼️ AI 생성 이미지 배경(DALL·E 등)
- 🎬 장면 전환 효과(페이드/슬라이드)
- ⬆️ YouTube Data API 자동 업로드

이미 지원: 단색/그라데이션 배경, 로컬 이미지·동영상 삽입, 키워드 스톡 검색(Pexels),
한국어 음성(Edge TTS), 자막, 1080p/720p/480p/세로(쇼츠).

## 라이선스

코드는 자유롭게 사용하세요. 자동 다운로드되는 Noto Sans KR 폰트는
[SIL Open Font License](https://github.com/google/fonts/tree/main/ofl/notosanskr) 를 따릅니다.
