# CapCut Auto Editor — Backend (V1)

FastAPI 백엔드. 무음/멈춤/말더듬 자동 감지 → 컷 → Whisper 자막 → 클립 속성 조정 → CapCut 드래프트(`draft_content.json`) 출력.

## 실행

```bash
# 의존성 (이미 설치됨)
pip install fastapi "uvicorn[standard]" python-multipart pydantic \
            faster-whisper pydub scikit-image pillow pymediainfo pycapcut
# ffmpeg: 시스템 PATH 필요

# 서버 기동 (backend/ 에서)
uvicorn app.main:app --reload --port 8000
```

## 프론트엔드 (Vite + React + TS, Design 6장)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (백엔드 CORS 허용됨)
npm run build    # 타입체크 + 프로덕션 빌드
```

컴포넌트(`frontend/src/components/`): VideoUploader, AnalysisControls(WS 진행률),
ClipList(개별 해제), PropertyPanel(크롭/회전/뒤집기/줌/투명도/필터), PreviewCanvas, ExportButton.
API 클라이언트: `frontend/src/api.ts`, 타입: `frontend/src/types.ts`.

## 테스트

```bash
cd backend && python -m pytest tests/ -q
```

## API (Design 4)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/projects` | 업로드 + 프로젝트 생성 (multipart: file, name) |
| GET | `/projects/{id}` | 조회 |
| POST | `/projects/{id}/analyze` | 무음/멈춤/말더듬 분석 시작 (202) |
| WS | `/projects/{id}/analyze/ws` | 진행률 스트림 `{stage, progress}` |
| POST | `/projects/{id}/subtitle` | Whisper SRT 단독 생성 |
| GET | `/projects/{id}/segments` | keep segments |
| PATCH | `/projects/{id}/segments/{sid}` | props 수정 / enabled 토글 (FR-06) |
| POST | `/projects/{id}/preview` | 프레임 미리보기 (image/png) |
| POST | `/projects/{id}/draft` | CapCut 드래프트 생성 |

## Do 단계에서 확정된 사항 (Design 대비 차이)

1. **FilterType enum 은 영문** (`Enhance`, `Vivid`, ...) — Design 예시의 한글명(`고채도`)은 실제 부재.
   `metadata/filter_meta.py` 에서 실제 enum 검증. 밝기/채도 근사 권장: `Enhance`, `Vivid`.
2. **시간 단위 주의**: `trange`/`tim` 는 bare float 을 **마이크로초**로 해석.
   초 단위 값은 반드시 μs(int)로 변환 (`draft_builder._us`). 회귀 테스트로 고정.
3. **add_filter 는 filter 트랙 필요** — 필터 사용 세그먼트가 있을 때만 filter 트랙 추가.
4. SRT 생성은 분석 파이프라인에 통합 + `/subtitle` 단독 엔드포인트 둘 다 제공.

## 미포함 (Out of Scope, Plan 계승)

DB/멀티유저 인증, 트랜지션/애니메이션, ffmpeg 완성영상 렌더 미리보기,
CapCut 자동 export, 프론트엔드(별도 작업).
