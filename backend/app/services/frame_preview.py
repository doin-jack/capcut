"""프레임 미리보기 (Design 3.6 / FR-09).

ffmpeg로 time_sec 프레임 1장 추출 → Pillow로 props 적용.
CapCut 실제 렌더와 '근사'임을 UI에 명시.
"""
from __future__ import annotations

import io
import subprocess

from PIL import Image, ImageEnhance

from ..models.clip_props import ClipProps


def _grab_frame(video_path: str, time_sec: float) -> Image.Image:
    proc = subprocess.run(
        [
            "ffmpeg", "-ss", f"{time_sec:.3f}", "-i", video_path,
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
        ],
        check=True,
        capture_output=True,
    )
    return Image.open(io.BytesIO(proc.stdout)).convert("RGBA")


def render_preview(video_path: str, time_sec: float, props: ClipProps) -> bytes:
    img = _grab_frame(video_path, time_sec)
    w, h = img.size

    # crop (정규화 0~1 → 픽셀)
    if props.crop:
        c = props.crop
        left = int(c.x * w)
        top = int(c.y * h)
        right = int(min(w, (c.x + c.w) * w))
        bottom = int(min(h, (c.y + c.h) * h))
        if right > left and bottom > top:
            img = img.crop((left, top, right, bottom))

    # flip
    if props.flip_h:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if props.flip_v:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    # rotation (양수=반시계가 PIL 기본 → CapCut과 부호 방향만 근사)
    if props.rotation:
        img = img.rotate(-props.rotation, expand=True)

    # scale (균등)
    if props.scale != 1.0:
        img = img.resize((max(1, int(img.width * props.scale)),
                          max(1, int(img.height * props.scale))))

    # filter_type 근사: 'Vivid'/고채도류는 채도↑, 'Enhance'는 대비↑ 근사
    if props.filter_type:
        factor = 1.0 + (props.filter_intensity / 100.0) * 0.5  # 1.0~1.5
        name = props.filter_type.lower()
        if "vivid" in name or "satur" in name:
            img = ImageEnhance.Color(img).enhance(factor)
        else:
            img = ImageEnhance.Brightness(img).enhance(factor)

    # opacity → alpha
    if props.opacity < 1.0:
        alpha = img.split()[-1].point(lambda a: int(a * props.opacity))
        img.putalpha(alpha)

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
