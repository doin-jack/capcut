"""SRT 자막을 컷 타임라인으로 재매핑 (FR-07 보정).

transcriber 는 원본 시간 기준 SRT 를 만든다. 하지만 컷 편집 후 비디오는
keep 세그먼트만 이어 붙여 앞당겨지므로, 자막도 동일한 오프셋으로 재매핑해야
영상과 맞는다. 제거 구간 안의 자막은 버리고, 경계를 가로지르는 자막은
유지 구간별로 잘라 분할한다.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..models.project import SubtitleCue

# keep 세그먼트 1개: (원본 시작초, 원본 끝초, 컷 타임라인상 새 시작초)
TimelineSpan = tuple[float, float, float]

_TS = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")


def _to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(path: str) -> list[SubtitleCue]:
    """SRT 파일 → SubtitleCue 리스트. 인덱스 줄은 무시하고 타임코드+본문만 사용."""
    text = Path(path).read_text(encoding="utf-8-sig")
    cues: list[SubtitleCue] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip() != ""]
        ts_idx = next((i for i, ln in enumerate(lines) if _TS.search(ln)), None)
        if ts_idx is None:
            continue
        m = _TS.search(lines[ts_idx])
        start = _to_seconds(m.group(1), m.group(2), m.group(3), m.group(4))
        end = _to_seconds(m.group(5), m.group(6), m.group(7), m.group(8))
        body = " ".join(lines[ts_idx + 1:]).strip()
        if body:
            cues.append(SubtitleCue(start=start, end=end, text=body))
    return cues


def remap_cues(
    cues: list[SubtitleCue],
    timeline: list[TimelineSpan],
    *,
    min_dur: float = 0.04,
) -> list[SubtitleCue]:
    """각 자막을 keep 세그먼트와 교차시켜 컷 타임라인으로 옮긴다.

    - 제거 구간(어떤 keep 과도 안 겹침) 자막은 버림.
    - 두 keep 에 걸친 자막은 각 교집합으로 분할(본문 동일).
    """
    out: list[SubtitleCue] = []
    for cue in cues:
        for src_start, src_end, new_start in timeline:
            os_ = max(cue.start, src_start)
            oe = min(cue.end, src_end)
            if oe - os_ < min_dur:
                continue
            ns = new_start + (os_ - src_start)
            ne = new_start + (oe - src_start)
            out.append(SubtitleCue(start=ns, end=ne, text=cue.text))
    out.sort(key=lambda c: c.start)
    return out


def write_srt(cues: list[SubtitleCue], path: str) -> str:
    lines: list[str] = []
    for i, c in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{_fmt_ts(c.start)} --> {_fmt_ts(c.end)}")
        lines.append(c.text)
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return path


def remap_srt_file(
    src_srt: str,
    timeline: list[TimelineSpan],
    out_srt: str,
) -> str | None:
    """원본 SRT 를 컷 타임라인으로 재매핑해 새 파일로 저장. 살아남은 자막이 없으면 None."""
    remapped = remap_cues(parse_srt(src_srt), timeline)
    if not remapped:
        return None
    return write_srt(remapped, out_srt)
