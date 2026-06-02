"""FFmpeg을 사용한 오디오 추출."""
from pathlib import Path
import ffmpeg
import imageio_ffmpeg


class AudioExtractionError(Exception):
    """오디오 추출 실패."""


def _get_ffmpeg_path() -> str:
    """imageio-ffmpeg에 동봉된 FFmpeg 바이너리 경로 반환."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_audio(
    video_path: Path,
    output_wav_path: Path,
    sample_rate: int = 16000,
) -> Path:
    """동영상에서 16kHz mono WAV 오디오 추출.

    Args:
        video_path: 입력 동영상 경로
        output_wav_path: 출력 WAV 경로
        sample_rate: 샘플레이트 (Whisper는 16kHz 기준)

    Returns:
        출력 파일 경로 (성공 시 output_wav_path)

    Raises:
        AudioExtractionError: 파일 없음 또는 FFmpeg 오류
    """
    if not video_path.exists():
        raise AudioExtractionError(f"Video file not found: {video_path}")

    ffmpeg_bin = _get_ffmpeg_path()
    try:
        (
            ffmpeg
            .input(str(video_path))
            .output(
                str(output_wav_path),
                acodec="pcm_s16le",
                ac=1,
                ar=sample_rate,
                vn=None,  # 비디오 스트림 제외
            )
            .overwrite_output()
            .run(cmd=ffmpeg_bin, quiet=True, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        raise AudioExtractionError(f"FFmpeg error: {stderr}") from e

    if not output_wav_path.exists():
        raise AudioExtractionError("FFmpeg produced no output file")
    return output_wav_path
