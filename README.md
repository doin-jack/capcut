# CapCut 자동 편집 (capcut-auto-editor)

원본 영상을 업로드하면 **무음·멈춤·말더듬을 자동 컷 편집**하고, **Whisper로 SRT 자막을 자동 생성**하며,
**클립 속성(크롭/회전/뒤집기/줌/투명도/필터)을 웹 UI에서 조정·미리보기**한 뒤,
결과를 **CapCut 드래프트(`draft_content.json`)로 출력**하는 로컬 웹 애플리케이션.

생성된 드래프트를 CapCut에서 열어 최종 확인·내보내기 한다.

## 구성

```
frontend (React + Vite + TS)  ──REST/WS──▶  backend (FastAPI)  ──▶  CapCut draft folder
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                       analysis                subtitle                  draft
                  (pydub/ffmpeg/cv)          (faster-whisper)          (pyCapCut)
```

- **백엔드**: FastAPI + pyCapCut(드래프트 쓰기) + faster-whisper(자막) + pydub/OpenCV/skimage(감지)
- **프론트엔드**: Vite + React + TypeScript (6개 컴포넌트, WebSocket 진행률)

## 실행

### 사전 요구사항
- Python 3.13, Node 20+, **ffmpeg (시스템 PATH)**

### 백엔드
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
python -m pytest tests/ -q   # 테스트
```

### 프론트엔드
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

## 주요 사항

- **밝기/채도**는 pyCapCut에 직접 슬라이더가 없어 `FilterType` 프리셋(`Enhance`/`Vivid`) 근사로 매핑.
- 미리보기는 Pillow 기반 **근사** — 최종 렌더는 CapCut에서 확인.
- `trange`/`tim`은 bare float을 **마이크로초**로 해석 → 초 단위 값은 μs로 변환 (`draft_builder._us`).
- **V1 범위 외**: DB/멀티유저 인증, 트랜지션 자동화, ffmpeg 완성영상 렌더, CapCut 자동 export.

자세한 설계·분석 문서는 [`docs/`](docs/) 참조 (PDCA: Plan → Design → Do → Check).
