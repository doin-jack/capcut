"""faster-whisper 전사 + 한국어 의미 단위 SRT 생성 (Design 3.3 / FR-07).

인식 정확도 향상을 위해 core/ 파이프라인에 위임한다:
- core.transcriber.Transcriber: 기본 medium 모델 + VAD 필터 + temperature 폴백 +
  환각 임계값(no_speech/compression) + beam=5 + condition_on_previous_text=False 로
  한국어 인식 정확도를 높이고 환각/누락을 줄인다.
- core.srt_segmenter: 한국어 의미 단위(종결어미·연결어미·호흡·길이) 분할 + 환각 필터.
- core.srt_writer: SRT(UTF-8 BOM + CRLF) 작성.

반환 형태는 기존과 호환: (words, srt_path). words 는 core 의 Word(start, end, text)이며
stutter_detector 가 `from .transcriber import Word` 로 그대로 사용한다.
"""
from __future__ import annotations

from pathlib import Path

from core.srt_segmenter import SegmenterOptions, Word, segment_words_to_subtitles
from core.srt_writer import write_srt
from core.transcriber import Transcriber

__all__ = ["Word", "transcribe"]

# 모델 로드는 비싸므로 size별로 Transcriber(모델 인스턴스 보유)를 캐시한다.
_TRANSCRIBERS: dict[str, Transcriber] = {}


def _get(model_size: str) -> Transcriber:
    if model_size not in _TRANSCRIBERS:
        _TRANSCRIBERS[model_size] = Transcriber(
            model_size=model_size, device="cpu", compute_type="int8",
        )
    return _TRANSCRIBERS[model_size]


def transcribe(
    audio_path: str | Path,
    srt_out_path: str | Path,
    *,
    model_size: str = "medium",
    language: str | None = "ko",
) -> tuple[list[Word], str]:
    """오디오 → (단어 리스트, SRT 경로).

    단어 타임스탬프는 stutter/retake 감지에, SRT 는 자막 트랙에 쓰인다.
    SRT 는 core 의 한국어 의미 단위 분할로 작성된다.
    """
    result = _get(model_size).transcribe(Path(audio_path), language=language)
    subs = segment_words_to_subtitles(result.words, SegmenterOptions())
    srt_path = Path(srt_out_path)
    write_srt(subs, srt_path)
    return result.words, str(srt_path)
