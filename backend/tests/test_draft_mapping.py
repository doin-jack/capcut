"""속성 매핑 단위 테스트 (Design 7 step7: '각 속성 매핑 단위 테스트').

draft_builder 의 ClipProps → pyCapCut ClipSettings/CropSettings 변환 검증.
실제 CapCut 실행 없이 변환 로직만 확인.
"""
from __future__ import annotations

import pycapcut as cc

from app.models.clip_props import ClipProps, CropBox
from app.services.draft_builder import _us, crop_to_settings, props_to_clip_settings


def test_clip_settings_mapping():
    props = ClipProps(
        rotation=45.0, flip_h=True, flip_v=False,
        scale=1.5, opacity=0.7,
    )
    cs = props_to_clip_settings(props)
    assert cs.alpha == 0.7
    assert cs.rotation == 45.0
    assert cs.flip_horizontal is True
    assert cs.flip_vertical is False
    assert cs.scale_x == 1.5
    assert cs.scale_y == 1.5


def test_clip_settings_defaults():
    cs = props_to_clip_settings(ClipProps())
    assert cs.alpha == 1.0
    assert cs.rotation == 0.0
    assert cs.scale_x == 1.0 and cs.scale_y == 1.0


def test_crop_to_settings_full_frame():
    crop = CropBox(x=0.0, y=0.0, w=1.0, h=1.0)
    s = crop_to_settings(crop)
    assert (s.upper_left_x, s.upper_left_y) == (0.0, 0.0)
    assert (s.lower_right_x, s.lower_right_y) == (1.0, 1.0)
    assert s.upper_right_x == 1.0 and s.upper_right_y == 0.0
    assert s.lower_left_x == 0.0 and s.lower_left_y == 1.0


def test_crop_to_settings_quadrant():
    # 좌상단 1/4 영역
    crop = CropBox(x=0.0, y=0.0, w=0.5, h=0.5)
    s = crop_to_settings(crop)
    assert s.upper_left_x == 0.0 and s.upper_left_y == 0.0
    assert s.upper_right_x == 0.5 and s.upper_right_y == 0.0
    assert s.lower_left_x == 0.0 and s.lower_left_y == 0.5
    assert s.lower_right_x == 0.5 and s.lower_right_y == 0.5


def test_crop_clamped_to_one():
    crop = CropBox(x=0.8, y=0.8, w=0.5, h=0.5)  # 넘침 → 1.0 클램프
    s = crop_to_settings(crop)
    assert s.lower_right_x == 1.0
    assert s.lower_right_y == 1.0


def test_seconds_to_microseconds():
    # 회귀 방지: trange/tim 은 bare float 을 μs 로 해석하므로 초→μs 변환 필수
    assert _us(1.0) == 1_000_000
    assert _us(0.5) == 500_000
    assert _us(0.0) == 0


def test_filter_type_is_english_enum():
    # Design 리스크 #6 해소 확인: 영문 enum 멤버 존재, 한글명 부재
    assert hasattr(cc.FilterType, "Enhance")
    assert not hasattr(cc.FilterType, "고채도")
