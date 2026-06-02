"""영상 멈춤/중복 프레임 감지 (Design 3.2 / FR-03).

sample_fps로 다운샘플 → 인접 프레임 SSIM > thresh 연속 구간을 멈춤으로 판정.
OpenCV 프레임 추출 + skimage.metrics.structural_similarity.
"""
from __future__ import annotations

import cv2
from skimage.metrics import structural_similarity as ssim

from ..models.project import Region


def detect_freeze(
    video_path: str,
    *,
    ssim_thresh: float = 0.985,
    min_freeze_ms: int = 500,
    sample_fps: int = 5,
) -> list[Region]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(src_fps / sample_fps))
    min_freeze_s = min_freeze_ms / 1000.0

    regions: list[Region] = []
    prev_gray = None
    prev_t = 0.0
    run_start: float | None = None  # 현재 멈춤 구간 시작 시각
    frame_idx = 0

    while True:
        ret = cap.grab()
        if not ret:
            break
        if frame_idx % step != 0:
            frame_idx += 1
            continue
        ok, frame = cap.retrieve()
        frame_idx += 1
        if not ok:
            break

        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # SSIM 비용 절감을 위해 다운스케일
        gray = cv2.resize(gray, (160, 90))

        if prev_gray is not None:
            score = ssim(prev_gray, gray)
            if score >= ssim_thresh:
                if run_start is None:
                    run_start = prev_t
            else:
                if run_start is not None and (prev_t - run_start) >= min_freeze_s:
                    regions.append(Region(start=run_start, end=prev_t, reason="freeze"))
                run_start = None

        prev_gray = gray
        prev_t = t

    # 마지막 구간 마감
    if run_start is not None and (prev_t - run_start) >= min_freeze_s:
        regions.append(Region(start=run_start, end=prev_t, reason="freeze"))

    cap.release()
    return regions
