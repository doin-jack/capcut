"""cut_planner 여집합/병합 로직 테스트 (Design 3.5 / FR-05)."""
from __future__ import annotations

from app.models.project import Region
from app.services.cut_planner import plan_keep_segments


def _spans(segs):
    return [(round(s.src_start, 3), round(s.src_end, 3)) for s in segs]


def test_complement_basic():
    # 10초 영상, 무음 [2,4] 제거 → keep [0,2],[4,10]
    silence = [Region(start=2.0, end=4.0, reason="silence")]
    segs = plan_keep_segments(10.0, silence, [], [])
    assert _spans(segs) == [(0.0, 2.0), (4.0, 10.0)]


def test_union_overlap_merge():
    # 겹치는 제거 구간 병합 후 여집합
    silence = [Region(start=2.0, end=5.0, reason="silence")]
    freeze = [Region(start=4.0, end=6.0, reason="freeze")]
    segs = plan_keep_segments(10.0, silence, freeze, [])
    assert _spans(segs) == [(0.0, 2.0), (6.0, 10.0)]


def test_no_removal_keeps_whole():
    segs = plan_keep_segments(8.0, [], [], [])
    assert _spans(segs) == [(0.0, 8.0)]


def test_removal_at_start_and_end():
    silence = [Region(start=0.0, end=1.0), Region(start=9.0, end=10.0)]
    segs = plan_keep_segments(10.0, silence, [], [])
    assert _spans(segs) == [(1.0, 9.0)]


def test_tiny_keep_dropped():
    # [0,2] 제거, [2,2.02] keep(20ms<50ms) drop, [2.02,10] 와 갭<merge → 병합
    silence = [Region(start=0.0, end=2.0)]
    freeze = [Region(start=2.02, end=2.05)]
    segs = plan_keep_segments(10.0, silence, freeze, [])
    # 2~2.02 (20ms)와 2.05~10 사이 갭 30ms < merge_gap 120ms → 합쳐져 하나
    assert len(segs) == 1
    assert _spans(segs)[0][1] == 10.0
