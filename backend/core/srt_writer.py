"""SRT 자막 파일 출력."""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Subtitle:
    """SRT 자막 한 줄."""
    index: int
    start: float  # 초 단위
    end: float    # 초 단위
    text: str     # 줄바꿈은 \n 사용


def format_timestamp(seconds: float) -> str:
    """초 → SRT 시간 포맷 'HH:MM:SS,mmm'.

    밀리초는 반올림이 아닌 절삭(부동소수점 오차 누적 방지).
    """
    if seconds < 0:
        seconds = 0.0
    total_ms = int(seconds * 1000)
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(subtitles: Iterable[Subtitle], path: Path) -> None:
    """자막 리스트를 SRT 파일로 쓴다 (UTF-8 BOM + CRLF)."""
    lines: list[str] = []
    for sub in subtitles:
        # 텍스트 내부 \n을 \r\n으로 정규화
        normalized_text = sub.text.replace("\r\n", "\n").replace("\n", "\r\n")
        lines.append(f"{sub.index}")
        lines.append(f"{format_timestamp(sub.start)} --> {format_timestamp(sub.end)}")
        lines.append(normalized_text)
        lines.append("")  # 자막 간 빈 줄
    body = "\r\n".join(lines)
    if body:
        body += "\r\n"  # 마지막 자막 뒤 줄바꿈
    path.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
