"""SRT → 컷 타임라인 재매핑 테스트 (FR-07 보정).

컷으로 제거된 구간만큼 자막을 앞당기고, 제거 구간 안의 자막은 버린다.
"""
from __future__ import annotations

from app.models.project import SubtitleCue
from app.services.subtitle_remap import parse_srt, remap_cues, write_srt

SRT = """1
00:00:00,000 --> 00:00:01,000
hello

2
00:00:02,500 --> 00:00:03,500
gap-only

3
00:00:05,000 --> 00:00:06,000
world
"""


def _spans(cues):
    return [(round(c.start, 3), round(c.end, 3), c.text) for c in cues]


def test_parse_srt(tmp_path):
    p = tmp_path / "in.srt"
    p.write_text(SRT, encoding="utf-8")
    cues = parse_srt(str(p))
    assert _spans(cues) == [
        (0.0, 1.0, "hello"),
        (2.5, 3.5, "gap-only"),
        (5.0, 6.0, "world"),
    ]


def test_remap_shifts_by_removed_gap():
    # 원본 [2,4] 제거 → 타임라인 맵: keep [0,2]→new 0, keep [4,10]→new 2
    timeline = [(0.0, 2.0, 0.0), (4.0, 10.0, 2.0)]
    cues = [
        SubtitleCue(start=0.0, end=1.0, text="hello"),   # 첫 keep → 그대로 0~1
        SubtitleCue(start=5.0, end=6.0, text="world"),   # 둘째 keep → 2+(5-4)=3 ~ 2+(6-4)=4
    ]
    out = remap_cues(cues, timeline)
    assert _spans(out) == [(0.0, 1.0, "hello"), (3.0, 4.0, "world")]


def test_remap_drops_cue_in_removed_region():
    # [2,4] 제거. 자막 [2.5,3.5] 는 제거 구간 안 → 버려짐
    timeline = [(0.0, 2.0, 0.0), (4.0, 10.0, 2.0)]
    cues = [SubtitleCue(start=2.5, end=3.5, text="gap-only")]
    assert remap_cues(cues, timeline) == []


def test_remap_clips_boundary_spanning_cue():
    # 자막 [1.5,5.0] 이 제거구간 [2,4] 를 가로지름 → 양쪽 keep 에 맞춰 분할
    timeline = [(0.0, 2.0, 0.0), (4.0, 10.0, 2.0)]
    cues = [SubtitleCue(start=1.5, end=5.0, text="span")]
    out = remap_cues(cues, timeline)
    # [1.5,2.0] → new 1.5~2.0 / [4.0,5.0] → new 2.0~3.0
    assert _spans(out) == [(1.5, 2.0, "span"), (2.0, 3.0, "span")]


def test_write_then_parse_roundtrip(tmp_path):
    cues = [SubtitleCue(start=0.0, end=1.25, text="a"), SubtitleCue(start=3.0, end=4.0, text="b")]
    p = tmp_path / "out.srt"
    write_srt(cues, str(p))
    assert _spans(parse_srt(str(p))) == [(0.0, 1.25, "a"), (3.0, 4.0, "b")]
