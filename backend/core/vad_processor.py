"""Silero VAD를 사용한 음성 구간 감지."""
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from silero_vad import load_silero_vad, get_speech_timestamps


@dataclass
class SpeechSegment:
    """음성이 감지된 구간 (초 단위)."""
    start: float
    end: float


_vad_model = None


def _load_audio(audio_path: Path, sample_rate: int) -> torch.Tensor:
    """PCM16 WAV을 읽어 1-D float32 텐서로 반환.

    silero-vad의 read_audio()는 torchaudio 오디오 백엔드(torchaudio>=2.9는
    torchcodec)에 의존하지만, audio_extractor.extract_audio()가 항상
    16kHz mono pcm_s16le WAV을 생성하므로 표준 라이브러리 wave 모듈로
    직접 디코딩하여 추가 의존성 없이 동작한다.
    """
    with wave.open(str(audio_path), "rb") as wav:
        n_channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        framerate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    if sample_width != 2:
        raise ValueError(
            f"지원하지 않는 WAV 샘플 폭: {sample_width * 8}bit (16bit PCM 필요)"
        )
    if framerate != sample_rate:
        raise ValueError(
            f"WAV 샘플레이트 불일치: {framerate}Hz (기대값 {sample_rate}Hz)"
        )

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    return torch.from_numpy(np.ascontiguousarray(audio))


def _get_model():
    """VAD 모델 lazy 로드 (한 번만 로딩)."""
    global _vad_model
    if _vad_model is None:
        _vad_model = load_silero_vad()
    return _vad_model


def detect_speech_segments(
    audio_path: Path,
    sample_rate: int = 16000,
    min_speech_duration_ms: int = 250,
    min_silence_duration_ms: int = 500,
) -> list[SpeechSegment]:
    """오디오 파일에서 음성 구간을 감지하여 (start, end) 리스트 반환.

    Args:
        audio_path: 16kHz mono WAV 경로
        sample_rate: 샘플레이트
        min_speech_duration_ms: 최소 음성 길이 (이보다 짧은 구간은 무시)
        min_silence_duration_ms: 음성 구간 분리 기준 묵음 길이

    Returns:
        SpeechSegment 리스트 (시간 단위 초)
    """
    model = _get_model()
    audio = _load_audio(audio_path, sample_rate)
    timestamps = get_speech_timestamps(
        audio,
        model,
        sampling_rate=sample_rate,
        min_speech_duration_ms=min_speech_duration_ms,
        min_silence_duration_ms=min_silence_duration_ms,
    )
    return [
        SpeechSegment(
            start=ts["start"] / sample_rate,
            end=ts["end"] / sample_rate,
        )
        for ts in timestamps
    ]
