# Plan: CapCut 자동 편집 프로그램 (capcut-auto-editor)

> 작성일: 2026-06-02
> 단계: Plan (Plan Plus 방식)
> 다음 단계: `/pdca design capcut-auto-editor`

---

## 1. Overview

영상 편집자가 원본 영상을 업로드하면 **무음 구간·멈춤 장면·말더듬을 자동으로 컷 편집**하고,
**Whisper로 SRT 자막을 자동 생성**하며, **각 클립의 속성(크롭/회전/뒤집기/줌/투명도/밝기/채도)을
웹 UI에서 조정·미리보기**한 뒤, 그 결과를 **CapCut 드래프트(`draft_content.json`)로 출력**하는
로컬 웹 애플리케이션. 편집자는 생성된 드래프트를 CapCut에서 열어 최종 확인·내보내기 한다.

핵심 라이브러리: **pyCapCut** (https://github.com/GuanYixuan/pyCapCut) — 드래프트 *쓰기* 전담.

---

## 2. User Intent Discovery (Phase 1)

| 항목 | 내용 |
|------|------|
| **핵심 목적** | 원본 → 자동 컷편집 + 자동 자막 + 클립 속성 조정 → CapCut 드래프트 출력의 **통합 워크플로우** |
| **대상 사용자** | 영상 편집자 여러 명 (비개발자 포함) → 보기 좋은 UI + 향후 팀 공유 고려 |
| **미리보기 의미** | GUI(웹)에서 속성을 조정하면 프레임 이미지로 미리보기 → 만족 시 버튼으로 CapCut 드래프트 생성. 드래프트를 CapCut에서 열면 설정이 그대로 적용됨 |
| **버벅임 정의** | (1) 영상 멈춤/중복 프레임 + (2) 말더듬(반복어·필러) 둘 다 |

---

## 3. Alternatives Explored (Phase 2)

### Approach A: 데스크톱 GUI (PySide6) + pyCapCut
- Pros: 단일 Python 스택, `.exe` 배포 간편, 네이티브 프레임 미리보기
- Cons: Qt 학습곡선, 빌드 크기

### Approach B: 로컬 웹앱 (FastAPI + React) + pyCapCut — **선택됨**
- Pros: 보기 좋은 UI, 향후 팀 공유 웹서비스로 확장 가능, 컴포넌트 기반 타임라인 구현 용이
- Cons: Python + JS 두 스택, 배포 시 로컬 서버 구동 필요
- 선택 이유: "영상 편집자 여러 명" + "보기 좋은 UI/향후 팀 공유" 요구에 부합

### Approach C: CLI + 설정파일
- Pros: 가장 빠른 구현, 배치 처리에 강함
- Cons: 시각적 미리보기 없음 → "미리보기 버튼" 요구와 충돌 (탈락)

---

## 4. YAGNI Review (Phase 3)

### V1 포함 (Included)
- ✅ **CapCut 드래프트 출력** (필수) — 결과물 그 자체
- ✅ **영상 업로드 / 프로젝트 관리 UI** (필수) — 웹앱 골대
- ✅ **무음 구간 자동 컷편집** — pydub dB 임계값 + 최소길이
- ✅ **SRT 자막 자동 생성** — faster-whisper, 단어 단위 타임스탬프
- ✅ **클립별 속성 조정 + 프레임 미리보기** — 크롭/회전/뒤집기/줌/투명도/밝기/채도
- ✅ **버벅임 자동 감지** — 영상 멈춤(SSIM/프레임 중복) + 말더듬(반복어·필러)

### V1 제외 / 추후 (Out of Scope — Deferred)
- ⏭️ DB 기반 멀티유저 인증·권한 (V1은 파일 기반 단일 로컬)
- ⏭️ 트랜지션/효과/애니메이션 자동 적용
- ⏭️ ffmpeg 실제 렌더 기반 완성영상 미리보기 (V1은 프레임 근사 미리보기)
- ⏭️ CapCut 자동 실행/배치 export 제어
- ⏭️ 호스팅형 팀 공유 웹서비스 배포

### YAGNI 원칙
- 3줄로 되는 것을 추상화하지 않는다
- 가상의 미래 요구를 위해 설계하지 않는다 (V1은 파일 기반 store, DB 없음)

---

## 5. Architecture (Phase 4.1 — 승인됨)

```
React Frontend (Vite)
  업로드 │ 클립/타임라인 │ 속성 패널 │ 프레임 미리보기
            │ REST / WebSocket(진행률)
FastAPI Backend (Python)
  Analysis(무음 pydub / 멈춤 SSIM / 말더듬 텍스트)
  Subtitle(Whisper→SRT)
  Preview(ffmpeg 프레임 + 속성 적용)
  Draft Builder(pyCapCut → draft_content.json)
            ▼
  CapCut 드래프트 폴더 (열어서 편집/내보내기)
```

**핵심 제약**: pyCapCut은 드래프트를 *쓰기*만 한다. 컷/자막/속성 계산은 백엔드가 수행해
draft JSON에 기록하고, 실제 렌더링은 CapCut이 담당. 미리보기는 ffmpeg 프레임 기반 *근사*이며
CapCut 실제 렌더와 100% 동일하지 않다.

---

## 6. Key Components (Phase 4.2 — 승인됨)

### Backend (Python / FastAPI)
```
backend/
├── main.py
├── api/
│   ├── projects.py      # 프로젝트 CRUD, 영상 업로드
│   ├── analysis.py      # 무음/멈춤/말더듬 분석 (WebSocket 진행률)
│   ├── subtitle.py      # Whisper SRT 생성
│   ├── preview.py       # 클립 속성 미리보기 프레임 생성
│   └── draft.py         # CapCut 드래프트 생성/내보내기
├── services/
│   ├── silence_detector.py   # pydub: dB 임계값 + 최소길이
│   ├── freeze_detector.py    # ffmpeg/OpenCV SSIM → 정지/중복 프레임
│   ├── stutter_detector.py   # Whisper word timestamps → 반복어/필러
│   ├── transcriber.py        # faster-whisper → 단어 타임스탬프 + SRT
│   ├── frame_preview.py      # ffmpeg 프레임 추출 + Pillow 속성 적용
│   └── draft_builder.py      # pyCapCut → draft_content.json
├── models/
│   ├── project.py
│   └── clip_props.py
└── store/                    # 프로젝트 메타 JSON 저장 (파일 기반, DB 없음)
```

### Frontend (React / Vite)
```
frontend/src/
├── pages/ProjectEditor.tsx
├── components/
│   ├── VideoUploader.tsx
│   ├── ClipList.tsx
│   ├── PropertyPanel.tsx     # 크롭/줌/밝기/투명도 슬라이더
│   ├── PreviewCanvas.tsx     # "미리보기" 버튼 → 프레임 표시
│   ├── AnalysisControls.tsx  # 임계값 설정 + 실행
│   └── ExportButton.tsx      # "CapCut 드래프트 생성"
└── api/client.ts
```

**핵심 라이브러리**: FastAPI, pyCapCut, faster-whisper, pydub, ffmpeg(시스템),
OpenCV(또는 ffmpeg freezedetect), Pillow / React, Vite, TypeScript

---

## 7. Data Flow (Phase 4.3 — 승인됨)

### ① 업로드 & 분석
```
영상 업로드 → store/{project_id}/source.mp4
분석(WebSocket 진행률):
  silence_detector → [{start,end}] 무음
  freeze_detector  → [{start,end}] 멈춤
  transcriber      → words[{text,start,end}] + subtitle.srt
  stutter_detector → [{start,end}] 반복어/필러
컷 구간 = 무음 ∪ 멈춤 ∪ 말더듬 → keep segments 계산 → project.json 저장
```

### ② 속성 조정 & 미리보기
```
클립 선택 → 슬라이더 조정 → "미리보기" 클릭
POST /preview {clip_id, time, props}
frame_preview: ffmpeg 프레임 추출 → Pillow 속성 적용 → PNG 반환
PreviewCanvas 표시 → props를 project.json clip에 저장
```

### ③ 드래프트 생성
```
"CapCut 드래프트 생성" 클릭
draft_builder(pyCapCut):
  ScriptFile 생성
  video track: keep segments만 VideoSegment 추가 (컷 반영) + clip props 적용
  text track: subtitle.srt import → 자막 세그먼트
draft_content.json 저장 → CapCut에서 열어 확인/내보내기
```

### 데이터 모델 (핵심)
```python
Project { id, name, source_path, keep_segments[], subtitle_srt_path, clips[] }
Clip    { id, start, end, props: ClipProps }
ClipProps { crop, rotation, flip_h, flip_v, scale, opacity, brightness, saturation }
```

---

## 8. Success Criteria

1. 원본 영상 업로드 후 무음/멈춤/말더듬 구간이 자동 감지되어 클립 목록에 표시된다
2. Whisper가 SRT 자막을 생성하고 드래프트의 텍스트 트랙에 반영된다
3. 클립 속성(크롭/회전/뒤집기/줌/투명도/밝기/채도)을 UI에서 조정하면 프레임 미리보기에 반영된다
4. "드래프트 생성" 시 `draft_content.json`이 출력되고, **CapCut에서 열었을 때 컷·자막·속성이 모두 적용**된다
5. 분석 임계값(무음 dB·최소길이 등)을 UI에서 조절할 수 있다

---

## 9. Risks & Open Questions

| 리스크 | 영향 | 대응 |
|--------|------|------|
| **버벅임(말더듬) 감지 정확도** | 높음 | V1은 단순 규칙(연속 반복어/필러 사전)으로 시작, 임계값 노출. 과감지 시 사용자가 클립에서 해제 가능하게 |
| **pyCapCut 속성 API 매핑** | 중 | `/pdca do` 단계에서 3-source 검증(공식 GitHub + 예제 + issue)으로 각 속성 적용법 확인 |
| **미리보기 ≠ CapCut 실제 렌더** | 중 | 근사 미리보기임을 UI에 명시 |
| **CapCut 버전/드래프트 경로** | 중 | Windows CapCut 기준, 드래프트 폴더 경로 설정 가능하게 |
| **Whisper 처리 시간/모델 크기** | 중 | faster-whisper + 모델 크기 선택 옵션 |

---

## 10. Brainstorming Log (Phases 1-4)

- **Q1 핵심 목적**: 통합 워크플로우 선택
- **Q2 대상 사용자**: 영상 편집자 여러 명 → 웹앱 + 보기 좋은 UI
- **Q3 미리보기 의미**: GUI 속성 미리보기 → 드래프트 생성
- **Phase 2 아키텍처**: Approach B (FastAPI + React) 선택 (추천은 A였으나 사용자가 B 선택)
- **Phase 3 YAGNI**: 4개 선택 기능 모두 V1 포함 (무음/자막/속성+미리보기/버벅임)
- **버벅임 정의**: 영상 멈춤 + 말더듬 둘 다
- **Phase 4**: Architecture / Components / Data Flow 각각 사용자 승인 완료

---

## 11. Next Steps

```
Plan Plus 완료
문서: docs/01-plan/features/capcut-auto-editor.plan.md
다음 단계: /pdca design capcut-auto-editor
```
