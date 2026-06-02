"""Whisper 전사 + SRT 생성 (Design 3.3 / FR-07).

faster-whisper. word_timestamps=True 로 단어 단위 타임스탬프 + SRT.
transcribe() 반환: (segments(iterable), info).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel

# 모델은 비싸므로 size별 캐시
_MODELS: dict[str, WhisperModel] = {}


@dataclass
class Word:
    text: str
    start: float
    end: float


def _get_model(model_size: str) -> WhisperModel:
    if model_size not in _MODELS:
        # CPU 환경 기본값 (int8). GPU 사용 시 device="cuda" 로 교체 가능.
        _MODELS[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _MODELS[model_size]


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe(
    audio_path: str,
    srt_out_path: str | Path,
    *,
    model_size: str = "base",
    language: str | None = None,
) -> tuple[list[Word], str]:
    """반환: (words, srt_path)."""
    model = _get_model(model_size)
    segments, _info = model.transcribe(
        audio_path,
        word_timestamps=True,
        language=language,
    )

    words: list[Word] = []
    srt_lines: list[str] = []
    idx = 1
    for seg in segments:  # generator → 순회하며 소비
        text = (seg.text or "").strip()
        if text:
            srt_lines.append(str(idx))
            srt_lines.append(f"{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}")
            srt_lines.append(text)
            srt_lines.append("")
            idx += 1
        for w in (seg.words or []):
            wt = (w.word or "").strip()
            if wt:
                words.append(Word(text=wt, start=w.start, end=w.end))

    srt_path = Path(srt_out_path)
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return words, str(srt_path)
