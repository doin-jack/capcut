# CapCut 자동 편집 — 프로젝트 지침 (Claude 용)

영상 업로드 → 무음/반복테이크/말더듬 자동 컷 + Whisper 자막 → CapCut 드래프트 출력.
백엔드 FastAPI(`backend/`), 프론트 Vite+React(`frontend/`), 자막 엔진 `backend/core/`.

---

## 🟢 "프로그램 세팅해줘" / "세팅" / "처음 시작" 요청 시

다음을 **순서대로 자동 실행**한다 (사용자에게 단계마다 묻지 말 것):

1. **세팅 스크립트 실행** (의존성·ffmpeg·CapCut 경로 일괄 처리, 멱등):
   ```
   powershell -ExecutionPolicy Bypass -File setup.ps1
   ```
   - 빠른 확인만 원하면 `-SkipModel` 로 Whisper 모델(~1.5GB) 다운로드 생략.
2. **백엔드 기동** (ffmpeg 경로를 PATH에 넣어서, 백그라운드):
   ```
   cd backend
   $env:PATH = "<ffmpeg bin>;" + $env:PATH
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
   ```
3. **프론트엔드 기동** (백그라운드): `cd frontend; npm run dev`
4. `http://localhost:8000/health` 가 `{"status":"ok"}` 인지, 프론트 5173 이 200 인지 확인 후
   **http://localhost:5173 주소를 사용자에게 안내**한다.

세팅이 끝나면 CapCut 草稿 경로는 앱이 자동 탐지하므로 따로 입력할 필요 없다.

---

## ⚙️ 운영 시 반드시 지킬 것 (실전에서 겪은 함정)

- **ffmpeg는 PATH 필수**: 백엔드를 띄울 때 ffmpeg bin 경로를 `$env:PATH` 앞에 넣어야
  pydub/whisper가 동작한다. 경로는 보통
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*-full_build\bin`.
- **`--reload` 쓰지 말 것**: 프로젝트 경로에 한글(`캡컷`)이 있어 WatchFiles 자동 리로드가
  변경을 자주 놓친다. 백엔드 코드를 고치면 **수동 재시작**한다.
- **드래프트 재생성 시 CapCut 잠금**: 같은 이름 드래프트가 CapCut에서 열려 있으면 `.locked`
  로 덮어쓰기가 막혀 PermissionError(→ UI에서 409 메시지)가 난다. 새 이름으로 만들거나
  사용자에게 CapCut에서 닫으라고 안내한다.
- **포트 정리**: 8000 재시작 시 죽은 reloader가 좀비 소켓을 남길 수 있다.
  `Get-NetTCPConnection -LocalPort 8000` PID + netstat 로 워커까지 확인해 종료한다.
- **커밋 금지 대상**: `backend/store/`(영상·wav), `.venv/`, `node_modules/` (.gitignore 처리됨).

---

## 🧠 자막/컷 파이프라인 핵심

- 전사: `backend/core/`(medium 모델 + VAD + 한국어 의미 단위 분할). 기본 모델 `medium`.
- 컷: 무음(`silence_detector`) ∪ 반복테이크(`retake_detector`) ∪ 말더듬(`stutter_detector`).
  - **freeze(멈춤)는 기본 OFF** — 정적 콘텐츠를 99% 오컷하던 문제 때문. opt-in.
  - 반복 테이크 = 같은 말 다시 한 NG를 발화 단위 퍼지 매칭으로 마지막 완성본만 남김.
- 자막은 컷 타임라인으로 **재매핑**(`subtitle_remap`)되어 영상과 정렬된다.
- 컷이 너무 급하면 `keep_padding_ms`(기본 200) 를 올린다.

## 테스트
```
cd backend; .\.venv\Scripts\python.exe -m pytest tests/ -q   # ffmpeg PATH 필요
cd frontend; npx tsc -b --noEmit
```
