"""Askript 웹앱 (FastAPI).

브라우저에서 대본을 붙여넣고 옵션을 골라 '영상 만들기' 를 누르면, 서버가
백그라운드로 mp4 를 렌더링하고 진행률을 보여준 뒤 미리보기/다운로드를 제공한다.

로컬 실행:
    pip install -r requirements.txt
    uvicorn webapp:app --reload
배포(Railway):
    Dockerfile 로 자동 빌드, PORT 환경변수에 바인딩.
"""

from __future__ import annotations

import os
import tempfile
import threading
import traceback
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from askript import fonts
from askript.parser import parse_color, parse_script
from askript.models import Background
from askript.render import RenderOptions, render_scenes

app = FastAPI(title="Askript")

OUTPUT_DIR = os.environ.get("ASKRIPT_OUTPUT", os.path.join(tempfile.gettempdir(), "askript_out"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

RESOLUTIONS = {
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "480p": (854, 480),
    "shorts": (1080, 1920),
}

# 진행 중/완료된 작업 상태 (메모리). job_id -> dict
JOBS: Dict[str, dict] = {}

# 한글 폰트는 한 번만 해석해 캐시.
_FONT: Optional[str] = None
_FONT_LOCK = threading.Lock()


def get_font() -> str:
    global _FONT
    with _FONT_LOCK:
        if _FONT is None:
            _FONT = fonts.resolve_font()
        return _FONT


def _default_background(style: str, bg_color: str, grad_top: str, grad_bottom: str) -> Background:
    if style == "color":
        return Background(kind="color", color=parse_color(bg_color))
    return Background(
        kind="gradient",
        color=parse_color(grad_top),
        color2=parse_color(grad_bottom),
    )


def _run_job(job_id: str, script: str, default_bg: Background, options: RenderOptions) -> None:
    job = JOBS[job_id]
    try:
        job["status"] = "rendering"
        options.font_path = get_font()
        scenes = parse_script(script, default_bg)
        if not scenes:
            raise ValueError("대본에서 장면을 찾지 못했습니다. 내용을 확인하세요.")
        job["total"] = sum(max(1, len(s.segments)) for s in scenes)

        def progress(i, total, text):
            job["progress"] = i
            job["total"] = total
            job["message"] = text

        render_scenes(scenes, options, progress=progress)
        job["status"] = "done"
    except Exception as e:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = str(e)
        traceback.print_exc()


@app.post("/api/generate")
def generate(
    script: str = Form(...),
    voice: str = Form("ko-KR-SunHiNeural"),
    tts: str = Form("auto"),
    style: str = Form("gradient"),
    bg_color: str = Form("#101418"),
    grad_top: str = Form("#001027"),
    grad_bottom: str = Form("#0a3d91"),
    rate: str = Form("+0%"),
    resolution: str = Form("1080p"),
    fit: str = Form("cover"),
    pexels_key: str = Form(""),
):
    if not script.strip():
        return JSONResponse({"error": "대본을 입력하세요."}, status_code=400)
    if resolution not in RESOLUTIONS:
        resolution = "1080p"

    job_id = uuid.uuid4().hex[:12]
    out_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
    try:
        default_bg = _default_background(style, bg_color, grad_top, grad_bottom)
        default_bg.fit = fit if fit in ("cover", "contain") else "cover"
    except ValueError as e:
        return JSONResponse({"error": f"색상 오류: {e}"}, status_code=400)

    tts_backend = tts if tts in ("auto", "edge", "gtts", "silent") else "auto"
    options = RenderOptions(
        out_path=out_path,
        size=RESOLUTIONS[resolution],
        fps=30,
        tts_backend=tts_backend,
        voice=voice,
        rate=rate or "+0%",
        pexels_key=pexels_key.strip() or None,
    )
    JOBS[job_id] = {"status": "queued", "progress": 0, "total": 0, "message": "", "out": out_path}
    threading.Thread(
        target=_run_job, args=(job_id, script, default_bg, options), daemon=True
    ).start()
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "작업을 찾을 수 없습니다."}, status_code=404)
    return {
        "status": job["status"],
        "progress": job.get("progress", 0),
        "total": job.get("total", 0),
        "message": job.get("message", ""),
        "error": job.get("error"),
    }


@app.get("/api/video/{job_id}")
def video(job_id: str):
    job = JOBS.get(job_id)
    if not job or job["status"] != "done":
        return JSONResponse({"error": "아직 준비되지 않았습니다."}, status_code=404)
    return FileResponse(
        job["out"], media_type="video/mp4", filename=f"askript_{job_id}.mp4"
    )


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML


INDEX_HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Askript — 대본을 영상으로</title>
<style>
  :root { --bg:#0c1018; --card:#161c28; --line:#28313f; --fg:#e8edf4; --mut:#90a0b5; --acc:#4c8dff; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Apple SD Gothic Neo","Noto Sans KR",sans-serif; }
  .wrap { max-width:840px; margin:0 auto; padding:28px 18px 60px; }
  h1 { font-size:26px; margin:0 0 4px; }
  .sub { color:var(--mut); margin:0 0 22px; font-size:14px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:16px; }
  label { display:block; font-size:13px; color:var(--mut); margin:0 0 6px; }
  textarea, input, select { width:100%; background:#0e131c; color:var(--fg); border:1px solid var(--line); border-radius:9px; padding:11px 12px; font-size:14px; font-family:inherit; }
  textarea { min-height:200px; resize:vertical; line-height:1.6; }
  .row { display:flex; gap:12px; flex-wrap:wrap; }
  .row > div { flex:1; min-width:140px; }
  .mt { margin-top:14px; }
  button { background:var(--acc); color:#fff; border:0; border-radius:10px; padding:13px 20px; font-size:15px; font-weight:600; cursor:pointer; }
  button:disabled { opacity:.55; cursor:default; }
  .hint { font-size:12px; color:var(--mut); margin-top:6px; line-height:1.6; }
  code { background:#0e131c; padding:1px 6px; border-radius:5px; color:#a9c7ff; }
  .bar { height:10px; background:#0e131c; border-radius:6px; overflow:hidden; border:1px solid var(--line); }
  .bar > i { display:block; height:100%; width:0; background:var(--acc); transition:width .3s; }
  .err { color:#ff7b7b; }
  video { width:100%; border-radius:10px; margin-top:6px; background:#000; }
  a.dl { display:inline-block; margin-top:10px; color:var(--acc); }
  .hidden { display:none; }
  .grad-only, .color-only { }
</style>
</head>
<body>
<div class="wrap">
  <h1>🎬 Askript</h1>
  <p class="sub">대본을 붙여넣으면 음성·자막·배경을 입혀 동영상(mp4)으로 만들어 줍니다.</p>

  <div class="card">
    <label>대본 (빈 줄로 장면 구분, <code>@title</code> <code>@bg</code> <code>@search</code> 지시어 사용 가능)</label>
    <textarea id="script" placeholder="@title 첫 장면&#10;안녕하세요. 첫 번째 문장입니다.&#10;두 번째 문장입니다.&#10;&#10;@search video 우주&#10;다음 장면입니다."></textarea>
    <p class="hint">웹 버전에서는 서버에 없는 로컬 파일 경로(<code>@bg image 내파일.png</code>)는 쓸 수 없습니다. 대신 <code>@search 키워드</code>(Pexels)로 이미지·영상을 넣으세요.</p>
  </div>

  <div class="card">
    <div class="row">
      <div>
        <label>목소리</label>
        <select id="voice">
          <option value="ko-KR-SunHiNeural">선희 (여성)</option>
          <option value="ko-KR-InJoonNeural">인준 (남성)</option>
          <option value="ko-KR-HyunsuMultilingualNeural">현수 (멀티)</option>
        </select>
      </div>
      <div>
        <label>음성</label>
        <select id="tts">
          <option value="auto">실제 음성 (자동: Edge→Google)</option>
          <option value="gtts">Google 음성 (gTTS)</option>
          <option value="edge">Edge 음성만</option>
          <option value="silent">무음 (미리보기)</option>
        </select>
      </div>
      <div>
        <label>해상도</label>
        <select id="resolution">
          <option value="1080p">1080p 가로</option>
          <option value="720p">720p 가로</option>
          <option value="shorts">세로 (쇼츠)</option>
        </select>
      </div>
    </div>

    <div class="row mt">
      <div>
        <label>기본 배경</label>
        <select id="style">
          <option value="gradient">그라데이션</option>
          <option value="color">단색</option>
        </select>
      </div>
      <div class="grad-field">
        <label>그라데이션 위 색</label>
        <input type="color" id="grad_top" value="#001027">
      </div>
      <div class="grad-field">
        <label>그라데이션 아래 색</label>
        <input type="color" id="grad_bottom" value="#0a3d91">
      </div>
      <div class="color-field hidden">
        <label>단색</label>
        <input type="color" id="bg_color" value="#101418">
      </div>
    </div>

    <div class="row mt">
      <div>
        <label>말하기 속도 (예: +10%, -10%)</label>
        <input id="rate" value="+0%">
      </div>
      <div>
        <label>Pexels API 키 (<code>@search</code> 사용 시)</label>
        <input id="pexels_key" placeholder="선택 사항">
      </div>
    </div>
    <p class="hint">Pexels 키는 <a href="https://www.pexels.com/api/" target="_blank" style="color:var(--acc)">여기</a>서 무료 발급. 환경변수 <code>PEXELS_API_KEY</code> 로 서버에 미리 넣어두면 매번 입력 안 해도 됩니다.</p>
  </div>

  <button id="go">영상 만들기</button>

  <div class="card mt hidden" id="progress-card">
    <label id="status-label">준비 중…</label>
    <div class="bar"><i id="bar"></i></div>
    <p class="hint" id="status-msg"></p>
    <p class="err hidden" id="err"></p>
  </div>

  <div class="card hidden" id="result-card">
    <label>완성된 영상</label>
    <video id="player" controls></video>
    <a class="dl" id="dl" download>⬇️ 다운로드</a>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);

function syncStyle() {
  const grad = $('style').value === 'gradient';
  document.querySelectorAll('.grad-field').forEach(e => e.classList.toggle('hidden', !grad));
  document.querySelector('.color-field').classList.toggle('hidden', grad);
}
$('style').addEventListener('change', syncStyle);
syncStyle();

let timer = null;

async function start() {
  const script = $('script').value.trim();
  if (!script) { alert('대본을 입력하세요.'); return; }

  $('go').disabled = true;
  $('progress-card').classList.remove('hidden');
  $('result-card').classList.add('hidden');
  $('err').classList.add('hidden');
  $('bar').style.width = '0%';
  $('status-label').textContent = '대기열에 넣는 중…';

  const fd = new FormData();
  fd.append('script', script);
  fd.append('voice', $('voice').value);
  fd.append('tts', $('tts').value);
  fd.append('style', $('style').value);
  fd.append('bg_color', $('bg_color').value);
  fd.append('grad_top', $('grad_top').value);
  fd.append('grad_bottom', $('grad_bottom').value);
  fd.append('rate', $('rate').value);
  fd.append('resolution', $('resolution').value);
  fd.append('pexels_key', $('pexels_key').value);

  let res;
  try { res = await fetch('/api/generate', { method:'POST', body: fd }); }
  catch (e) { return fail('서버에 연결할 수 없습니다.'); }
  const data = await res.json();
  if (!res.ok) return fail(data.error || '요청 실패');

  poll(data.job_id);
}

function poll(jobId) {
  timer = setInterval(async () => {
    let s;
    try { s = await (await fetch('/api/status/' + jobId)).json(); }
    catch (e) { return; }
    if (s.status === 'rendering' || s.status === 'queued') {
      const pct = s.total ? Math.round(s.progress / s.total * 100) : 5;
      $('bar').style.width = Math.max(pct, 5) + '%';
      $('status-label').textContent =
        s.status === 'queued' ? '준비 중…' : `만드는 중… (${s.progress}/${s.total})`;
      $('status-msg').textContent = s.message || '';
    } else if (s.status === 'done') {
      clearInterval(timer);
      $('bar').style.width = '100%';
      $('status-label').textContent = '완료 ✅';
      $('status-msg').textContent = '';
      const url = '/api/video/' + jobId;
      $('player').src = url;
      $('dl').href = url;
      $('result-card').classList.remove('hidden');
      $('go').disabled = false;
    } else if (s.status === 'error') {
      clearInterval(timer);
      fail(s.error || '렌더링 실패');
    }
  }, 1200);
}

function fail(msg) {
  if (timer) clearInterval(timer);
  $('status-label').textContent = '실패';
  const e = $('err'); e.textContent = msg; e.classList.remove('hidden');
  $('go').disabled = false;
}

$('go').addEventListener('click', start);
</script>
</body>
</html>
"""
