# Design: CapCut 자동 편집 프로그램 (capcut-auto-editor)

> 작성일: 2026-06-02
> 단계: Design
> Plan 참조: `docs/01-plan/features/capcut-auto-editor.plan.md`
> 다음 단계: `/pdca do capcut-auto-editor`

---

## 0. pyCapCut API 검증 결과 (구현의 전제)

실제 라이브러리 소스(clone)를 검증하여 확정한 사실:

| 속성 | pyCapCut 지원 방식 | 매핑 |
|------|-------------------|------|
| **투명도(opacity)** | `ClipSettings.alpha` (0~1) | 직접 |
| **회전(rotation)** | `ClipSettings.rotation` (각도, ±) | 직접 |
| **뒤집기(flip)** | `ClipSettings.flip_horizontal / flip_vertical` (bool) | 직접 |
| **줌/스케일(scale)** | `ClipSettings.scale_x / scale_y` (배율) | 직접 |
| **위치(position)** | `ClipSettings.transform_x / transform_y` (반화면 단위) | 직접 |
| **크롭(crop)** | `VideoMaterial(crop_settings=CropSettings(...))` — 8개 꼭짓점 좌표(0~1) | 소재 단위 |
| **밝기/채도(brightness/saturation)** | ❌ 직접 슬라이더 없음 → `ScriptFile.add_filter(FilterType.X, intensity 0~100)` 프리셋 | **필터 프리셋 매핑** (사용자 승인) |

**핵심 API 시그니처** (검증됨):
```python
import pycapcut as cc
from pycapcut import trange, tim

folder = cc.DraftFolder(r"<CapCut 草稿 폴더>")
script = folder.create_draft("name", 1920, 1080, fps=30, allow_replace=True)
script.add_track(cc.TrackType.video).add_track(cc.TrackType.text)

# 크롭이 필요하면 VideoMaterial을 먼저 생성
mat = cc.VideoMaterial(path, crop_settings=cc.CropSettings(upper_left_x=0.1, ...))
seg = cc.VideoSegment(
    mat,                                   # 또는 path(크롭 없을 때)
    target_timerange=trange(start_us, dur_us),   # 트랙상 위치/길이
    source_timerange=trange(src_start, src_dur), # 원본에서 잘라올 구간 (컷편집 핵심)
    clip_settings=cc.ClipSettings(alpha=..., rotation=..., scale_x=..., flip_horizontal=...)
)
script.add_segment(seg)
script.add_filter(cc.FilterType.고채도, trange(start, dur), intensity=80)  # 밝기/채도 근사
script.import_srt(srt_path, track_name="자막", text_style=cc.TextStyle(size=5, align=1))
script.save()
```

> 시간 단위: pyCapCut 내부는 **마이크로초(μs)**. `trange("1.5s","4s")` 또는 `tim()` 헬퍼 사용.
> 플랫폼: 草稿 생성은 크로스플랫폼이나, **export는 Windows CapCut 필요** (V1은 export 미포함).

---

## 1. 시스템 구성

```
frontend (React + Vite + TS)  ──REST/WS──▶  backend (FastAPI)  ──▶  CapCut draft folder
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                       analysis                subtitle                  draft
                  (pydub/ffmpeg/cv)          (faster-whisper)          (pyCapCut)
```

---

## 2. 데이터 모델 (Pydantic)

```python
# models/clip_props.py
class ClipProps(BaseModel):
    crop: CropBox | None = None        # {x, y, w, h} 정규화 0~1 → CropSettings 8꼭짓점 변환
    rotation: float = 0.0              # 각도
    flip_h: bool = False
    flip_v: bool = False
    scale: float = 1.0                 # scale_x = scale_y = scale (균등 줌)
    opacity: float = 1.0               # → alpha
    filter_type: str | None = None     # FilterType enum name (밝기/채도 근사)
    filter_intensity: float = 100.0    # 0~100

# models/project.py
class Segment(BaseModel):              # 컷 후 "유지 구간"
    id: str
    src_start: float                   # 원본 기준 초
    src_end: float
    props: ClipProps = ClipProps()

class SubtitleCue(BaseModel):
    start: float; end: float; text: str

class Project(BaseModel):
    id: str
    name: str
    source_path: str
    duration: float
    fps: int
    width: int; height: int
    segments: list[Segment] = []       # keep segments (컷 결과)
    detected: DetectedRegions = ...     # 무음/멈춤/말더듬 원본 구간 (참고용)
    subtitle_srt_path: str | None = None
    capcut_draft_path: str | None = None

class DetectedRegions(BaseModel):
    silence: list[Region]
    freeze: list[Region]
    stutter: list[Region]              # Region = {start, end, reason}
```

저장: `store/{project_id}/project.json` (V1 파일 기반, DB 없음).
원본/산출물: `store/{project_id}/source.mp4`, `subtitle.srt`, `frames/`.

---

## 3. 서비스 인터페이스

### 3.1 silence_detector.py (무음)
```python
def detect_silence(audio_path: str, *, min_silence_ms: int = 700,
                   silence_thresh_db: float = -40.0,
                   keep_padding_ms: int = 100) -> list[Region]:
    """pydub.silence.detect_silence 기반. dB 임계값·최소길이는 API 노출 파라미터."""
```
- 근거: pydub `detect_silence(min_silence_len, silence_thresh)` 표준 API.

### 3.2 freeze_detector.py (영상 멈춤/중복 프레임)
```python
def detect_freeze(video_path: str, *, ssim_thresh: float = 0.985,
                  min_freeze_ms: int = 500, sample_fps: int = 5) -> list[Region]:
    """sample_fps로 다운샘플 → 인접 프레임 SSIM > thresh 연속 구간을 멈춤으로 판정.
    구현: OpenCV로 프레임 추출 + skimage.metrics.structural_similarity.
    대안: ffmpeg `freezedetect` 필터(noise/duration)도 가능."""
```

### 3.3 transcriber.py (Whisper)
```python
def transcribe(audio_path: str, *, model_size: str = "base",
               language: str | None = None) -> tuple[list[Word], str]:
    """faster-whisper. word_timestamps=True로 단어 단위 타임스탬프 + SRT 생성.
    반환: (words[{text,start,end}], srt_path)"""
```
- 근거: faster-whisper `WhisperModel.transcribe(word_timestamps=True)`.

### 3.4 stutter_detector.py (말더듬)
```python
FILLERS_KO = {"음", "어", "그", "저기", "이제"}
def detect_stutter(words: list[Word], *, repeat_window: int = 2,
                   max_gap_ms: int = 400) -> list[Region]:
    """규칙 기반 V1:
    (1) 인접 동일 단어 반복 (w[i].text == w[i+1].text, gap < max_gap)
    (2) 필러 단어(FILLERS_KO) 단독 출현
    → 해당 단어 타임스탬프 구간을 stutter Region으로."""
```
> 정확도 리스크: 과감지 가능 → UI에서 개별 구간 해제 가능 (FR 참조).

### 3.5 cut_planner.py (컷 통합)
```python
def plan_keep_segments(duration: float,
                       silence: list[Region], freeze: list[Region],
                       stutter: list[Region]) -> list[Segment]:
    """제거 구간 = silence ∪ freeze ∪ stutter (병합) → 여집합 = keep segments.
    인접 keep 구간 사이 작은 갭은 병합. 각 keep → Segment(src_start, src_end)."""
```

### 3.6 frame_preview.py (미리보기)
```python
def render_preview(video_path: str, time_sec: float,
                   props: ClipProps) -> bytes:
    """ffmpeg로 time_sec 프레임 1장 추출(JPEG) → Pillow로 props 적용:
       crop→crop(), rotation→rotate(), flip→transpose(),
       scale→resize, opacity→putalpha, filter_type→ImageEnhance 근사.
    반환: PNG bytes. (CapCut 실제 렌더와 근사임을 UI 명시)"""
```

### 3.7 draft_builder.py (pyCapCut)
```python
def build_draft(project: Project, draft_folder: str) -> str:
    """1) DraftFolder(draft_folder).create_draft(name, W, H, fps, allow_replace=True)
       2) add_track(video) + add_track(text)
       3) keep segments 순회:
            track 누적 위치 = 이전 세그먼트 끝
            crop 있으면 VideoMaterial(crop_settings=...) 먼저 생성
            VideoSegment(material/path,
                target_timerange=trange(track_pos, dur),
                source_timerange=trange(seg.src_start, dur),
                clip_settings=ClipSettings(alpha, rotation, scale_x/y, flip_h/v))
            add_segment
            props.filter_type 있으면 add_filter(FilterType[name], 해당 trange, intensity)
       4) import_srt(subtitle.srt, track_name="자막")
       5) script.save() → draft 경로 반환"""
```

---

## 4. API 명세 (FastAPI)

| Method | Path | 설명 | 입력 | 출력 |
|--------|------|------|------|------|
| POST | `/projects` | 프로젝트 생성 + 영상 업로드 | multipart(file, name) | `Project` |
| GET | `/projects/{id}` | 프로젝트 조회 | — | `Project` |
| POST | `/projects/{id}/analyze` | 무음/멈춤/말더듬 분석 시작 | `{params}` | 202 + job_id |
| WS | `/projects/{id}/analyze/ws` | 분석 진행률 스트림 | — | `{stage, progress}` |
| POST | `/projects/{id}/subtitle` | Whisper SRT 생성 | `{model_size, lang}` | `{srt_path, cues[]}` |
| GET | `/projects/{id}/segments` | keep segments 조회 | — | `Segment[]` |
| PATCH | `/projects/{id}/segments/{sid}` | 세그먼트 props 수정/해제 | `ClipProps` 또는 `{enabled}` | `Segment` |
| POST | `/projects/{id}/preview` | 프레임 미리보기 | `{sid, time, props}` | `image/png` |
| POST | `/projects/{id}/draft` | CapCut 드래프트 생성 | `{draft_folder}` | `{draft_path}` |

분석 파라미터(`/analyze`): `min_silence_ms, silence_thresh_db, ssim_thresh, min_freeze_ms` — 모두 UI 노출.

---

## 5. 기능 요구사항 매핑 (FR)

| FR | 내용 | 담당 |
|----|------|------|
| FR-01 | 영상 업로드 & 프로젝트 생성 | `api/projects.py` |
| FR-02 | 무음 구간 자동 감지 (임계값 조절) | `silence_detector` |
| FR-03 | 영상 멈춤 감지 | `freeze_detector` |
| FR-04 | 말더듬(반복어/필러) 감지 | `stutter_detector` + `transcriber` |
| FR-05 | 컷 통합 → keep segments | `cut_planner` |
| FR-06 | 감지 구간 개별 해제(과감지 대응) | `PATCH /segments/{sid}` |
| FR-07 | SRT 자막 자동 생성 | `transcriber` |
| FR-08 | 클립 속성 조정(크롭/회전/뒤집기/줌/투명도/필터) | `PropertyPanel` + `ClipProps` |
| FR-09 | 프레임 미리보기 | `frame_preview` |
| FR-10 | CapCut 드래프트 출력 | `draft_builder` |

---

## 6. 프론트엔드 컴포넌트

| 컴포넌트 | 역할 | 주요 상태/호출 |
|----------|------|---------------|
| `VideoUploader` | 드래그&드롭 업로드 | `POST /projects` |
| `AnalysisControls` | 임계값 슬라이더 + 실행 | `POST /analyze`, WS 진행률 |
| `ClipList` | keep/감지 구간 목록, 체크박스 해제 | `GET/PATCH /segments` |
| `PropertyPanel` | 크롭/회전/뒤집기/줌/투명도/필터 슬라이더 | local props state |
| `PreviewCanvas` | "미리보기" 버튼 → PNG 표시 | `POST /preview` |
| `ExportButton` | "CapCut 드래프트 생성" | `POST /draft` |

---

## 7. 구현 순서 (Do 단계용)

1. 프로젝트 스캐폴드 (backend FastAPI + frontend Vite) + pyCapCut/faster-whisper/pydub 설치
2. `models/` (Project/Segment/ClipProps) + 파일 기반 store
3. `api/projects.py` 업로드 + 메타 추출(pymediainfo/ffprobe)
4. `silence_detector` → `freeze_detector` → `transcriber` → `stutter_detector` → `cut_planner`
5. `api/analyze` + WebSocket 진행률
6. `frame_preview` + `POST /preview`
7. `draft_builder` (pyCapCut) + `POST /draft` — **각 속성 매핑 단위 테스트**
8. 프론트엔드 컴포넌트 (Uploader → Controls → ClipList → PropertyPanel → Preview → Export)
9. 통합 E2E: 업로드→분석→자막→속성→드래프트, CapCut에서 열어 검증

---

## 8. 의존성 설치

```bash
# backend
pip install fastapi uvicorn[standard] python-multipart pydantic \
            pyCapCut faster-whisper pydub opencv-python scikit-image \
            pillow pymediainfo
# ffmpeg: 시스템 설치 필요 (PATH)

# frontend
npm create vite@latest frontend -- --template react-ts
npm i axios
```

---

## 9. 리스크 & 완화 (Design 시점)

| 리스크 | 완화 |
|--------|------|
| 말더듬 과감지 | FR-06 개별 해제, 필러 사전·반복 임계값 UI 노출 |
| 밝기/채도 = 필터 근사 | UI에 "필터 프리셋(근사)" 명시, 미리보기는 정확 표시 |
| 미리보기 ≠ CapCut 렌더 | "근사 미리보기" 라벨, 최종은 CapCut에서 확인 |
| Whisper 처리시간 | model_size 선택(tiny~base) + WS 진행률 |
| CapCut 草稿 경로/버전 | draft_folder 사용자 설정값으로 받음 |
| FilterType 정확 enum명 | Do 단계에서 `metadata/filter_meta.py` 실제 enum명으로 매핑 테이블 확정 |

---

## 10. Out of Scope (Plan 계승)

DB/멀티유저 인증, 트랜지션/애니메이션 자동화, ffmpeg 완성영상 렌더 미리보기,
CapCut 자동 export 제어, 호스팅형 팀 웹서비스.
