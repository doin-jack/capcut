"""분석 파이프라인 실행 + 진행률 (Design 3.4~3.5, 4 /analyze).

silence → freeze → transcriber → stutter → cut_planner 순서.
진행률은 asyncio.Queue 로 WS에 스트림.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from . import store
from .services import (
    audio_util,
    cut_planner,
    freeze_detector,
    silence_detector,
    stutter_detector,
    transcriber,
)
from .models.project import DetectedRegions


@dataclass
class AnalyzeParams:
    min_silence_ms: int = 700
    silence_thresh_db: float = -40.0
    ssim_thresh: float = 0.985
    min_freeze_ms: int = 500
    model_size: str = "base"
    language: str | None = None


@dataclass
class Job:
    project_id: str
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    done: bool = False


# project_id → Job
_jobs: dict[str, Job] = {}


def get_job(project_id: str) -> Job | None:
    return _jobs.get(project_id)


async def _emit(job: Job, stage: str, progress: float) -> None:
    await job.queue.put({"stage": stage, "progress": progress})


async def run_analysis(project_id: str, params: AnalyzeParams) -> None:
    """백그라운드 태스크. blocking 작업은 to_thread 로 오프로드."""
    job = Job(project_id=project_id)
    _jobs[project_id] = job
    try:
        project = store.load(project_id)
        if project is None:
            await _emit(job, "error", 0.0)
            return

        pdir = store.project_dir(project_id)

        await _emit(job, "audio", 0.05)
        wav = await asyncio.to_thread(audio_util.extract_wav, project.source_path, pdir)

        await _emit(job, "silence", 0.15)
        silence = await asyncio.to_thread(
            silence_detector.detect_silence_regions,
            wav,
            min_silence_ms=params.min_silence_ms,
            silence_thresh_db=params.silence_thresh_db,
        )

        await _emit(job, "freeze", 0.35)
        freeze = await asyncio.to_thread(
            freeze_detector.detect_freeze,
            project.source_path,
            ssim_thresh=params.ssim_thresh,
            min_freeze_ms=params.min_freeze_ms,
        )

        await _emit(job, "transcribe", 0.55)
        srt_path = pdir / "subtitle.srt"
        words, srt = await asyncio.to_thread(
            transcriber.transcribe,
            wav,
            srt_path,
            model_size=params.model_size,
            language=params.language,
        )

        await _emit(job, "stutter", 0.8)
        stutter = await asyncio.to_thread(stutter_detector.detect_stutter, words)

        await _emit(job, "plan", 0.9)
        segments = cut_planner.plan_keep_segments(
            project.duration, silence, freeze, stutter,
        )

        project.detected = DetectedRegions(silence=silence, freeze=freeze, stutter=stutter)
        project.segments = segments
        project.subtitle_srt_path = srt
        store.save(project)

        await _emit(job, "done", 1.0)
    except Exception as exc:  # 진행률 채널로 에러 전파
        await job.queue.put({"stage": "error", "progress": 0.0, "detail": str(exc)})
    finally:
        job.done = True
