"""클립 속성 모델 (Design 2 / FR-08).

pyCapCut ClipSettings/CropSettings 로 매핑되는 속성들.
밝기/채도는 직접 슬라이더가 없어 FilterType 프리셋(근사)으로 매핑한다.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CropBox(BaseModel):
    """정규화(0~1) 크롭 박스. CropSettings 8꼭짓점으로 변환된다."""

    x: float = Field(0.0, ge=0.0, le=1.0)
    y: float = Field(0.0, ge=0.0, le=1.0)
    w: float = Field(1.0, gt=0.0, le=1.0)
    h: float = Field(1.0, gt=0.0, le=1.0)


class ClipProps(BaseModel):
    crop: CropBox | None = None          # → CropSettings 8꼭짓점
    rotation: float = 0.0                # 각도 (±)
    flip_h: bool = False
    flip_v: bool = False
    scale: float = Field(1.0, gt=0.0)    # scale_x = scale_y = scale (균등 줌)
    opacity: float = Field(1.0, ge=0.0, le=1.0)  # → alpha
    filter_type: str | None = None       # FilterType enum name (밝기/채도 근사)
    filter_intensity: float = Field(100.0, ge=0.0, le=100.0)
