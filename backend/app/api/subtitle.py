"""Whisper SRT 생성 단독 엔드포인트 (Design 4 /subtitle / FR-07).

분석 파이프라인과 별개로 자막만 재생성하고 싶을 때 사용.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import store
from ..models.project import SubtitleCue
from ..services import audio_util, transcriber

router = APIRouter(prefix="/projects", tags=["subtitle"])


class SubtitleRequest(BaseModel):
    model_size: str = "medium"
    lang: str | None = None


class SubtitleResponse(BaseModel):
    srt_path: str
    cues: list[SubtitleCue]


@router.post("/{project_id}/subtitle")
async def make_subtitle(project_id: str, req: SubtitleRequest) -> SubtitleResponse:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(404, "project not found")

    pdir = store.project_dir(project_id)
    wav = await asyncio.to_thread(audio_util.extract_wav, project.source_path, pdir)
    srt_path = pdir / "subtitle.srt"
    words, srt = await asyncio.to_thread(
        transcriber.transcribe, wav, srt_path,
        model_size=req.model_size, language=req.lang,
    )

    # 단어 → 문장 단위 cue 근사 (간단 묶음)
    cues: list[SubtitleCue] = []
    if words:
        buf, start = [], words[0].start
        for w in words:
            buf.append(w.text)
            if w.text.endswith((".", "?", "!", "。")) or len(buf) >= 12:
                cues.append(SubtitleCue(start=start, end=w.end, text=" ".join(buf)))
                buf, start = [], w.end
        if buf:
            cues.append(SubtitleCue(start=start, end=words[-1].end, text=" ".join(buf)))

    project.subtitle_srt_path = srt
    store.save(project)
    return SubtitleResponse(srt_path=srt, cues=cues)
