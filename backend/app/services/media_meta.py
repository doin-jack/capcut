"""영상 메타 추출 (Design 7-3: pymediainfo/ffprobe)."""
from __future__ import annotations

from pymediainfo import MediaInfo


def extract_meta(video_path: str) -> dict:
    """duration(초), fps, width, height 추출.

    pymediainfo(libmediainfo) 사용. 누락 시 안전한 기본값으로 대체.
    """
    info = MediaInfo.parse(video_path)
    duration = 0.0
    fps = 30
    width = 1920
    height = 1080

    for track in info.tracks:
        if track.track_type == "Video":
            if track.duration:
                duration = float(track.duration) / 1000.0  # ms → s
            if track.frame_rate:
                fps = round(float(track.frame_rate))
            if track.width:
                width = int(track.width)
            if track.height:
                height = int(track.height)
            break
        if track.track_type == "General" and track.duration and not duration:
            duration = float(track.duration) / 1000.0

    return {"duration": duration, "fps": fps, "width": width, "height": height}
