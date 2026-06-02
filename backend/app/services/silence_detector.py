"""무음 감지 (Design 3.1 / FR-02).

pydub.silence.detect_silence 기반. dB 임계값·최소길이는 API 노출 파라미터.
detect_silence 반환: [[start_ms, end_ms], ...]
"""
from __future__ import annotations

from pydub import AudioSegment
from pydub.silence import detect_silence

from ..models.project import Region


def detect_silence_regions(
    audio_path: str,
    *,
    min_silence_ms: int = 700,
    silence_thresh_db: float = -40.0,
    keep_padding_ms: int = 100,
) -> list[Region]:
    audio = AudioSegment.from_file(audio_path)
    raw = detect_silence(
        audio,
        min_silence_len=min_silence_ms,
        silence_thresh=silence_thresh_db,
    )

    regions: list[Region] = []
    for start_ms, end_ms in raw:
        # 무음 양끝에 padding 만큼 음성을 남겨 부자연스러운 컷 방지
        s = (start_ms + keep_padding_ms) / 1000.0
        e = (end_ms - keep_padding_ms) / 1000.0
        if e > s:
            regions.append(Region(start=s, end=e, reason="silence"))
    return regions
