# Askript 웹앱 — Railway 등에서 자동 빌드/배포용
FROM python:3.11-slim

# 한글 폰트(나눔) + fontconfig 설치 (자막 렌더링용).
# ffmpeg 는 imageio-ffmpeg 번들 바이너리를 사용하므로 별도 설치 불필요.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-nanum fontconfig \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    ASKRIPT_OUTPUT=/tmp/askript_out

EXPOSE 8000

# Railway 가 PORT 환경변수를 주입한다. main.py 가 파이썬에서 직접 PORT 를 읽어
# 바인딩하므로, 셸 변수 확장에 의존하지 않는다.
CMD ["python", "main.py"]
