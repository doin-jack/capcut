"""반복 테이크 / 말 더듬(false start) 감지 (FR-04 확장).

화자가 같은 말을 여러 번 다시 하는 경우(인트로 NG 등), 발화(utterance) 단위로
'앞선 발화가 뒤따르는 더 완성된 발화의 덜 완성된 시도'이면 앞쪽을 제거 대상으로 본다.
→ 마지막 완성 테이크만 남는다.

stutter_detector(단어 인접 반복/필러)는 발화 '내부' 더듬을, 이쪽은 발화 '사이'
반복 테이크를 담당한다. 둘은 상호 보완적이며 cut_planner 에서 합쳐진다.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Protocol

from ..models.project import Region


class _Utterance(Protocol):
    start: float
    end: float
    text: str


def _norm(text: str) -> str:
    """비교용 정규화: 공백/구두점 제거 + 소문자."""
    return re.sub(r"[^\w가-힣]", "", text).lower()


def _is_retake(a: str, b: str, *, sim_thresh: float) -> bool:
    """a 가 b 의 '덜 완성된 시도'인가? (a 가 b 의 퍼지 선두에 포함)."""
    if not a or not b:
        return False
    if a == b:
        return True
    # a 가 b 의 앞부분과 충분히 유사하면 false start 로 판단
    prefix = b[: len(a) + 3]
    return SequenceMatcher(None, a, prefix).ratio() >= sim_thresh


def detect_retakes(
    utterances: list[_Utterance],
    *,
    window: int = 4,
    max_span_s: float = 10.0,
    sim_thresh: float = 0.62,
) -> list[Region]:
    """앞선 발화가 가까운 뒤 발화(window/max_span 이내)의 덜 완성된 시도이면 제거.

    체이닝으로 연속 반복(안녕하세요×N)도 마지막 1개만 남기고 모두 제거된다.
    """
    norms = [_norm(u.text) for u in utterances]
    n = len(utterances)
    regions: list[Region] = []
    for i in range(n):
        ai = norms[i]
        if not ai:
            continue
        for j in range(i + 1, min(i + 1 + window, n)):
            if utterances[j].start - utterances[i].start > max_span_s:
                break
            if _is_retake(ai, norms[j], sim_thresh=sim_thresh):
                # 제거 구간을 '다음 발화 시작'까지 확장해 botched take 의 트레일링
                # 숨소리·꼬리음(발화 사이 침묵)까지 함께 제거 → keep 슬라이버 방지.
                nxt = utterances[i + 1].start if i + 1 < n else utterances[i].end
                end = max(utterances[i].end, nxt)
                regions.append(Region(start=utterances[i].start, end=end, reason="retake"))
                break
    return regions
