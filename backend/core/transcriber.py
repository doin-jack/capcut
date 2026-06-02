"""faster-whisper 음성 인식 래퍼."""
import os

# huggingface_hub 1.x는 대용량 모델 파일을 Xet 백엔드로 내려받는데, 일부
# 네트워크 환경에서 0바이트로 멈춘다. 클래식 HTTPS LFS 다운로드로 폴백한다.
# huggingface_hub.constants가 import 시점에 이 변수를 읽으므로
# faster_whisper import보다 먼저 설정해야 한다.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from faster_whisper import WhisperModel

from core.srt_segmenter import Word


@dataclass
class TranscriptionResult:
    """인식 결과."""
    words: list[Word]
    language: str
    duration: float


# 환각/누락 균형 임계값 — 너무 엄격하면 정상 발화도 폐기됨
_NO_SPEECH_PROB_THRESHOLD = 0.85
_COMPRESSION_RATIO_THRESHOLD = 2.8

# 디코딩 실패 시 단계적으로 temperature를 올려 재시도(표준 Whisper 동작)
_TEMPERATURE_FALLBACK = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

# VAD가 짧은 침묵에 너무 민감하면 단어가 잘리므로 완화
_VAD_PARAMETERS = {
    "min_silence_duration_ms": 500,
    "speech_pad_ms": 400,
}


class Transcriber:
    """faster-whisper 모델 래퍼.

    모델 인스턴스를 보유해 재사용한다 (모델 로드는 비싸므로).
    """

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = "ko",
        beam_size: int = 5,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> TranscriptionResult:
        """오디오 파일을 인식해 단어 리스트 반환.

        Args:
            audio_path: 16kHz mono WAV 경로
            language: 언어 코드 ('ko', 'en' 등), None이면 자동 감지
            beam_size: 빔 서치 크기
            progress_callback: 진행률(0.0~1.0) 콜백

        Returns:
            TranscriptionResult
        """
        model = self._get_model()
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=beam_size,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=_VAD_PARAMETERS,
            condition_on_previous_text=False,
            temperature=_TEMPERATURE_FALLBACK,
            no_speech_threshold=_NO_SPEECH_PROB_THRESHOLD,
            compression_ratio_threshold=_COMPRESSION_RATIO_THRESHOLD,
        )

        words: list[Word] = []
        total_duration = info.duration or 0.0
        for segment in segments_iter:
            # 환각 가능성 높은 세그먼트 폐기
            if segment.no_speech_prob > _NO_SPEECH_PROB_THRESHOLD:
                continue
            if segment.compression_ratio > _COMPRESSION_RATIO_THRESHOLD:
                continue
            if not segment.words:
                continue
            for w in segment.words:
                text = (w.word or "").strip()
                if not text:
                    continue
                words.append(Word(start=float(w.start), end=float(w.end), text=text))
            # 진행률 갱신
            if progress_callback and total_duration > 0:
                progress = min(1.0, segment.end / total_duration)
                progress_callback(progress)

        # 마지막에 강제 100% 호출 (총 길이 정확치 않을 경우 대비)
        if progress_callback:
            progress_callback(1.0)

        return TranscriptionResult(
            words=words,
            language=info.language,
            duration=info.duration,
        )
