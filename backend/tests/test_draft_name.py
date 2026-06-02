"""드래프트 저장 이름 정리 테스트."""
from __future__ import annotations

from app.services.draft_builder import sanitize_draft_name


def test_keeps_simple_korean_name():
    assert sanitize_draft_name("강의1") == "강의1"


def test_strips_illegal_chars():
    assert sanitize_draft_name('강의:1/2*?"<>|') == "강의12"


def test_collapses_whitespace_and_trailing_dot():
    assert sanitize_draft_name("  내   영상 .  ") == "내 영상"


def test_empty_falls_back():
    assert sanitize_draft_name("") == "untitled"
    assert sanitize_draft_name(None) == "untitled"
    assert sanitize_draft_name("   ") == "untitled"


def test_length_capped():
    assert len(sanitize_draft_name("가" * 200)) == 80
