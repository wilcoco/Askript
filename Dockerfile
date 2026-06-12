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

# Railway 는 PORT 환경변수를 주입한다 (없으면 8000).
CMD ["sh", "-c", "uvicorn webapp:app --host 0.0.0.0 --port ${PORT:-8000}"]
