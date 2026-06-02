# Gap Analysis: CapCut 자동 편집 프로그램 (capcut-auto-editor)

> 분석일: 2026-06-02
> 단계: Check (Gap Analysis)
> Design 참조: `docs/02-design/features/capcut-auto-editor.design.md`
> 구현 루트: `backend/`
> 범위: **백엔드 한정** (Design 6장 프론트엔드는 의도적으로 보류됨)

---

## Match Rate 요약

| 범위 | Match Rate | 상태 |
|------|:----------:|:----:|
| **백엔드 한정** (Design 2·3·4·5 백엔드 FR·7장 step 1-7,9) | **100%** | 우수 |
| **전체 기능** (보류된 6장 프론트엔드 / FR-08 UI / step 8 포함) | **~88%** | 양호 (프론트 보류) |

**권장**: 백엔드 Do 범위는 100% → **report 진행** (`/pdca report`). 프론트엔드는 별도 Do 범위이며 결함이 아님.

---

## 2장 — Pydantic 모델 (100% 존재)

| 모델 | Design 필드 | 구현 | 상태 |
|------|------------|------|------|
| `CropBox` | x, y, w, h (0~1) | `models/clip_props.py` (`Field` 범위 검증) | Match (+검증) |
| `ClipProps` | crop, rotation, flip_h, flip_v, scale, opacity, filter_type, filter_intensity | 전부 존재·검증 | Match |
| `Region` | start, end, reason | `models/project.py` | Match |
| `Segment` | id, src_start, src_end, props | + `enabled: bool` 추가 | Match (+FR-06 필드) |
| `SubtitleCue` | start, end, text | 존재 | Match |
| `DetectedRegions` | silence, freeze, stutter | 존재 | Match |
| `Project` | id, name, source_path, duration, fps, width, height, segments, detected, subtitle_srt_path, capcut_draft_path | 전부 존재 | Match |

`Segment.enabled` 는 2장 스니펫에 명시되지 않았으나 FR-06 및 PATCH `{enabled}` 본문이 요구 → 설계 일관 추가. 결함 아님.

## 3장 — 서비스 인터페이스 (7/7 구현)

| # | Design 함수 | 구현 | 일치 |
|---|------------|------|------|
| 3.1 | `detect_silence(...)` | `silence_detector.detect_silence_regions` | Match (이름에 `_regions` 접미사, 호출부 일관) |
| 3.2 | `detect_freeze(...)` | `freeze_detector.detect_freeze` | Match (OpenCV+SSIM, 다운스케일 최적화) |
| 3.3 | `transcribe(...)` | `transcriber.transcribe` | Match+개선 (`srt_out_path` 명시, 모델 캐시) |
| 3.4 | `detect_stutter(...)` | `stutter_detector.detect_stutter` | Match (FILLERS_KO 동일, 규칙 일치) |
| 3.5 | `plan_keep_segments(...)` | `cut_planner.plan_keep_segments` | Match (+`min_keep_s`/`merge_gap_s` 튜너블) |
| 3.6 | `render_preview(...)` | `frame_preview.render_preview` | Match |
| 3.7 | `build_draft(...)` | `draft_builder.build_draft` | Match (+필터 트랙 처리 개선) |

개선 사항(결함 아님):
- `build_draft` 는 필요 시에만 **filter 트랙**을 추가하고 `track_name`/`intensity` 를 `add_filter` 에 전달 — Design 의사코드보다 정확.
- 시간 단위 μs 변환(`_us`) 추가 — Design 47행 함정 해소.

## 4장 — API 엔드포인트 (9/9 존재)

| Design | 구현 | 상태 |
|--------|------|------|
| POST `/projects` | `api/projects.py` create_project | Match |
| GET `/projects/{id}` | get_project (404) | Match |
| POST `/analyze` | `api/analyze.py` start_analyze (202+job_id) | Match |
| WS `/analyze/ws` | analyze_ws (`{stage,progress}`) | Match |
| POST `/subtitle` | `api/subtitle.py` (`{srt_path,cues[]}`) | Match |
| GET `/segments` | `api/editing.py` list_segments | Match |
| PATCH `/segments/{sid}` | patch_segment (props OR enabled) | Match |
| POST `/preview` | preview (image/png) | Match |
| POST `/draft` | make_draft (`{draft_path}`) | Match |

분석 파라미터(`min_silence_ms, silence_thresh_db, ssim_thresh, min_freeze_ms`) 전부 노출. CORS(Vite) + `/health` 추가.

## 5장 — 기능 요구사항 (FR-01..FR-10)

| FR | 백엔드 코드 | 상태 |
|----|------------|------|
| FR-01 | `api/projects.py` + `media_meta` | Match |
| FR-02 | `silence_detector` + 파라미터 | Match |
| FR-03 | `freeze_detector` | Match |
| FR-04 | `stutter_detector` + `transcriber` | Match |
| FR-05 | `cut_planner` | Match |
| FR-06 | PATCH `/segments/{sid}` + `enabled`, `build_draft` 반영 | Match |
| FR-07 | `transcriber` + `/subtitle` | Match |
| FR-08 | `ClipProps` + `props_to_clip_settings`/`crop_to_settings` (백엔드) / `PropertyPanel`=프론트 보류 | 백엔드 Match, UI 보류 |
| FR-09 | `frame_preview` + `/preview` | Match |
| FR-10 | `draft_builder` + `/draft` | Match |

## 7장 — 구현 순서

| Step | 항목 | 상태 |
|------|------|------|
| 1 | 백엔드 스캐폴드 + 의존성 | Done (프론트 스캐폴드 보류) |
| 2 | models + 파일 store | Done |
| 3 | projects 업로드 + 메타 | Done |
| 4 | silence→freeze→transcriber→stutter→cut_planner | Done |
| 5 | analyze API + WS | Done (`analysis_runner` asyncio.Queue) |
| 6 | frame_preview + /preview | Done |
| 7 | draft_builder + /draft + **속성 매핑 단위 테스트** | Done (`test_draft_mapping.py`) |
| 8 | 프론트엔드 컴포넌트 | **보류 (Out of Scope)** |
| 9 | E2E 통합 | 부분 — 백엔드 테스트 통과; 실 CapCut E2E 는 수동(V1 export 제외) |

테스트: `test_cut_planner.py`(여집합/병합/엣지) + `test_draft_mapping.py`(속성 매핑/μs 회귀/필터 enum). 총 12개 통과.

## 해소된 항목 (결함 아님)

- **리스크 #6 (FilterType enum명):** `metadata/filter_meta.py` 가 실제 영문 enum(`Enhance`, `Vivid`, `Vivid_2`) 사용·검증. `test_filter_type_is_english_enum` 가 한글명 부재 확인. 정상.

## 보류 / Out-of-Scope (결함 아님)

- **프론트엔드 (6장):** VideoUploader, AnalysisControls, ClipList, PropertyPanel, PreviewCanvas, ExportButton — 백엔드 엔드포인트는 모두 준비됨.
- **전체 E2E (step 9) + CapCut export:** V1 export 제외(§0/§10), 실 CapCut 검증은 수동.

## 선택적 Design 문서 보정 (정확한 이름 일치용)

- [ ] 2장에 `Segment.enabled` 필드 문서화
- [ ] `detect_silence_regions` 이름 / `transcribe(srt_out_path)` 시그니처 반영
- [ ] 3.7 의 전용 filter 트랙 방식 명시
- [ ] `cut_planner` `min_keep_s`/`merge_gap_s` 튜너블 문서화

---

## 권장

- 백엔드 Do 범위: **100% → `/pdca report capcut-auto-editor` 진행**
- 전체 기능: ~88% (프론트 보류) → 프론트엔드(6장) + E2E(step 9)를 후속 Do 범위로 추적. 백엔드는 iterate 불필요.
