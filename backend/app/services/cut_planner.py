"""컷 통합 (Design 3.5 / FR-05).

제거 구간 = silence ∪ freeze ∪ stutter (병합) → 여집합 = keep segments.
인접 keep 구간 사이 작은 갭은 병합.
"""
from __future__ import annotations

import uuid

from ..models.project import Region, Segment


def _merge(regions: list[Region]) -> list[tuple[float, float]]:
    """겹치거나 인접한 구간 병합. 정렬된 (start, end) 리스트 반환."""
    if not regions:
        return []
    spans = sorted(((r.start, r.end) for r in regions), key=lambda x: x[0])
    merged: list[list[float]] = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def plan_keep_segments(
    duration: float,
    silence: list[Region],
    freeze: list[Region],
    stutter: list[Region],
    *,
    min_keep_s: float = 0.05,
    merge_gap_s: float = 0.12,
) -> list[Segment]:
    removal = _merge(silence + freeze + stutter)

    # 여집합(keep) 계산
    keeps: list[tuple[float, float]] = []
    cursor = 0.0
    for s, e in removal:
        s = max(0.0, min(s, duration))
        e = max(0.0, min(e, duration))
        if s > cursor:
            keeps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < duration:
        keeps.append((cursor, duration))

    # 인접 keep 사이 작은 갭 병합
    merged_keeps: list[list[float]] = []
    for s, e in keeps:
        if merged_keeps and (s - merged_keeps[-1][1]) <= merge_gap_s:
            merged_keeps[-1][1] = e
        else:
            merged_keeps.append([s, e])

    segments: list[Segment] = []
    for s, e in merged_keeps:
        if (e - s) >= min_keep_s:
            segments.append(Segment(id=uuid.uuid4().hex[:8], src_start=s, src_end=e))
    return segments
