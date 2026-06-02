"""반복 테이크/false start 감지 테스트 (FR-04 확장).

발화 단위로, 앞선 발화가 뒤의 더 완성된 발화의 덜 완성된 시도이면 제거(마지막만 유지).
"""
from __future__ import annotations

from app.models.project import SubtitleCue
from app.services.retake_detector import detect_retakes


def _u(start, end, text):
    return SubtitleCue(start=start, end=end, text=text)


def _removed(regs):
    return [(round(r.start, 2), round(r.end, 2)) for r in regs]


def test_exact_repeat_keeps_last():
    # "안녕하세요" 3회 → 앞 2개 제거, 마지막 유지. 제거 구간은 다음 발화 시작까지 확장.
    us = [_u(0, 1, "안녕하세요."), _u(2, 3, "안녕하세요."), _u(4, 5, "안녕하세요.")]
    assert _removed(detect_retakes(us)) == [(0, 2), (2, 4)]


def test_false_start_prefix_removed():
    # 미완성 시도가 뒤의 완성 문장의 앞부분 → 제거(다음 발화 시작까지 확장)
    us = [
        _u(0, 2, "AI로 생산자 대기의 강의를 수강"),
        _u(3, 7, "AI로 생산자 대기 강의에 수강을 결정해 주신 수강생분들 반갑습니다"),
    ]
    assert _removed(detect_retakes(us)) == [(0, 3)]


def test_distinct_sentences_kept():
    # 서로 다른 문장은 제거하지 않음(과제거 방지)
    us = [
        _u(0, 2, "오늘은 날씨가 좋습니다"),
        _u(3, 5, "내일은 비가 옵니다"),
        _u(6, 8, "모레는 눈이 내립니다"),
    ]
    assert detect_retakes(us) == []


def test_beyond_time_span_kept():
    # 동일 문구라도 너무 멀리 떨어지면(>max_span) 반복 테이크로 보지 않음
    us = [_u(0, 1, "안녕하세요"), _u(30, 31, "안녕하세요")]
    assert detect_retakes(us, max_span_s=10.0) == []


def test_chain_with_interleaved_takes():
    # 안녕/안녕/미완성/안녕/완성 → 마지막 완성과 직전 안녕만 남김
    us = [
        _u(0, 1, "안녕하세요"),
        _u(2, 3, "안녕하세요"),
        _u(4, 6, "AI로 생산자 강의를"),
        _u(7, 8, "안녕하세요"),
        _u(9, 13, "AI로 생산자 강의를 신청해 주셔서 감사합니다"),
    ]
    removed = _removed(detect_retakes(us))
    # 첫 두 안녕과 미완성 take 제거(다음 발화 시작까지 확장). 마지막 안녕(7,8)은 유지
    assert removed == [(0, 2), (2, 4), (4, 7)]
    assert (9, 13) not in removed
