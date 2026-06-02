"""CapCut 드래프트 생성 (Design 3.7 / FR-10).

keep segments → VideoSegment (clip_settings 매핑) + 필터 + SRT 자막.
crop(정규화 x,y,w,h) → CropSettings 8꼭짓점(0~1) 변환.
"""
from __future__ import annotations

import pycapcut as cc
from pycapcut import trange

from ..metadata import filter_meta
from ..models.clip_props import ClipProps, CropBox
from ..models.project import Project, Segment

VIDEO_TRACK = "main_video"
TEXT_TRACK = "자막"
FILTER_TRACK = "filter"


def _us(seconds: float) -> int:
    """초 → 마이크로초. pyCapCut trange/tim 는 bare float 을 μs 로 해석하므로
    초 단위 값은 반드시 μs(int) 로 변환해 전달해야 한다 (Design 47행 참조)."""
    return int(round(seconds * 1_000_000))


def crop_to_settings(crop: CropBox) -> cc.CropSettings:
    """정규화 {x,y,w,h} → CropSettings 8꼭짓점(좌상/우상/좌하/우하)."""
    x0, y0 = crop.x, crop.y
    x1, y1 = min(1.0, crop.x + crop.w), min(1.0, crop.y + crop.h)
    return cc.CropSettings(
        upper_left_x=x0, upper_left_y=y0,
        upper_right_x=x1, upper_right_y=y0,
        lower_left_x=x0, lower_left_y=y1,
        lower_right_x=x1, lower_right_y=y1,
    )


def props_to_clip_settings(props: ClipProps) -> cc.ClipSettings:
    return cc.ClipSettings(
        alpha=props.opacity,
        rotation=props.rotation,
        flip_horizontal=props.flip_h,
        flip_vertical=props.flip_v,
        scale_x=props.scale,
        scale_y=props.scale,
    )


def build_draft(project: Project, draft_folder: str) -> str:
    folder = cc.DraftFolder(draft_folder)
    script = folder.create_draft(
        project.name, project.width, project.height,
        fps=project.fps, allow_replace=True,
    )
    script.add_track(cc.TrackType.video, VIDEO_TRACK)
    script.add_track(cc.TrackType.text, TEXT_TRACK)

    # 필터를 쓰는 세그먼트가 하나라도 있으면 필터 트랙 추가 (add_filter 전제)
    needs_filter = any(
        s.enabled and s.props.filter_type and filter_meta.is_valid(s.props.filter_type)
        for s in project.segments
    )
    if needs_filter:
        script.add_track(cc.TrackType.filter, FILTER_TRACK)

    track_pos = 0.0  # 트랙상 누적 위치 (초)
    for seg in project.segments:
        if not seg.enabled:
            continue
        dur = seg.src_end - seg.src_start
        if dur <= 0:
            continue

        props = seg.props
        # crop 있으면 VideoMaterial 먼저 생성
        if props.crop:
            material = cc.VideoMaterial(
                project.source_path,
                crop_settings=crop_to_settings(props.crop),
            )
            mat_or_path: object = material
        else:
            mat_or_path = project.source_path

        dur_us = _us(dur)
        video_seg = cc.VideoSegment(
            mat_or_path,
            target_timerange=trange(_us(track_pos), dur_us),
            source_timerange=trange(_us(seg.src_start), dur_us),
            clip_settings=props_to_clip_settings(props),
        )
        script.add_segment(video_seg, VIDEO_TRACK)

        # 밝기/채도 근사 필터
        if props.filter_type and filter_meta.is_valid(props.filter_type):
            script.add_filter(
                filter_meta.resolve(props.filter_type),
                trange(_us(track_pos), dur_us),
                track_name=FILTER_TRACK,
                intensity=props.filter_intensity,
            )

        track_pos += dur

    # 자막
    if project.subtitle_srt_path:
        script.import_srt(
            project.subtitle_srt_path,
            TEXT_TRACK,
            text_style=cc.TextStyle(size=5, align=1),
        )

    script.save()
    return script.save_path
