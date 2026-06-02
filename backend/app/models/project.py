"""프로젝트/세그먼트 모델 (Design 2)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .clip_props import ClipProps


class Region(BaseModel):
    """원본 기준 구간 (초). 감지 결과 / 제거 후보."""

    start: float
    end: float
    reason: str = ""


class Segment(BaseModel):
    """컷 후 '유지 구간'(keep segment)."""

    id: str
    src_start: float                     # 원본 기준 초
    src_end: float
    enabled: bool = True                 # FR-06: 개별 해제
    props: ClipProps = Field(default_factory=ClipProps)


class SubtitleCue(BaseModel):
    start: float
    end: float
    text: str


class DetectedRegions(BaseModel):
    silence: list[Region] = Field(default_factory=list)
    freeze: list[Region] = Field(default_factory=list)
    stutter: list[Region] = Field(default_factory=list)
    retake: list[Region] = Field(default_factory=list)   # 반복 테이크(false start)


class Project(BaseModel):
    id: str
    name: str
    source_path: str
    duration: float = 0.0
    fps: int = 30
    width: int = 1920
    height: int = 1080
    segments: list[Segment] = Field(default_factory=list)        # keep segments (컷 결과)
    detected: DetectedRegions = Field(default_factory=DetectedRegions)  # 참고용 원본 구간
    subtitle_srt_path: str | None = None
    capcut_draft_path: str | None = None
