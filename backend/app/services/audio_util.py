"""오디오 추출 헬퍼. ffmpeg로 영상→wav 추출 (pydub/whisper 공용)."""
from __future__ import annotations

import subprocess
from pathlib import Path


def extract_wav(video_path: str, out_dir: str | Path) -> str:
    """16kHz mono wav 추출. whisper/pydub 모두에 적합."""
    out = Path(out_dir) / "audio.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-ac", "1", "-ar", "16000", "-vn",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return str(out)
