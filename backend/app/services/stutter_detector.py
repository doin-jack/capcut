"""말더듬 감지 (Design 3.4 / FR-04).

규칙 기반 V1:
 (1) 인접 동일 단어 반복 (w[i].text == w[i+1].text, gap < max_gap)
 (2) 필러 단어(FILLERS_KO) 단독 출현
→ 해당 단어 타임스탬프 구간을 stutter Region으로.
과감지 리스크는 FR-06(개별 해제)로 대응.
"""
from __future__ import annotations

import re

from ..models.project import Region
from .transcriber import Word

FILLERS_KO = {"음", "어", "그", "저기", "이제"}


def _norm(text: str) -> str:
    """비교용 정규화: 구두점 제거 + 소문자."""
    return re.sub(r"[^\w가-힣]", "", text).lower()


def detect_stutter(
    words: list[Word],
    *,
    repeat_window: int = 2,
    max_gap_ms: int = 400,
) -> list[Region]:
    regions: list[Region] = []
    max_gap_s = max_gap_ms / 1000.0
    n = len(words)

    for i, w in enumerate(words):
        norm = _norm(w.text)
        if not norm:
            continue

        # (2) 필러 단독
        if norm in FILLERS_KO:
            regions.append(Region(start=w.start, end=w.end, reason="filler"))
            continue

        # (1) 인접 반복 (window 내 동일 단어 + gap 작음)
        for j in range(i + 1, min(i + 1 + repeat_window, n)):
            if _norm(words[j].text) == norm and (words[j].start - w.end) <= max_gap_s:
                regions.append(Region(start=w.start, end=w.end, reason="repeat"))
                break

    return regions
