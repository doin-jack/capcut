"""FilterType 매핑/검증 (Design 9 리스크 #6 해소).

실측 결과 pyCapCut FilterType enum 멤버명은 **영문**이다
(예: 'Enhance', 'Vivid', 'Blur' ...). Design 예시의 한글명('고채도')은 실제 존재하지 않음.
밝기/채도 '근사' 프리셋으로 'Enhance', 'Vivid' 등을 권장 노출한다.
"""
from __future__ import annotations

import pycapcut as cc

# 사용자 노출용 권장 프리셋(밝기/채도 근사). 실제 enum 멤버명만 포함.
SUGGESTED_FILTERS = ["Enhance", "Vivid", "Vivid_2"]


def all_filter_names() -> list[str]:
    return [n for n in dir(cc.FilterType) if not n.startswith("_")]


def is_valid(name: str) -> bool:
    return hasattr(cc.FilterType, name)


def resolve(name: str) -> "cc.FilterType":
    """enum 멤버 반환. 없으면 KeyError."""
    if not is_valid(name):
        raise KeyError(f"Unknown FilterType: {name!r}")
    return getattr(cc.FilterType, name)
