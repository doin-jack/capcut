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
    retake_detector,
    silence_detector,
    stutter_detector,
    subtitle_remap,
    transcriber,
)
from .models.project import DetectedRegions


@dataclass
class AnalyzeParams:
    min_silence_ms: int = 700
    silence_thresh_db: float = -40.0
    # 무음 양끝에 남길 여유(숨 쉬는 간격). 클수록 컷이 덜 급하고 말이 자연스러움.
    keep_padding_ms: int = 200
    ssim_thresh: float = 0.985
    min_freeze_ms: int = 500
    # 멈춤(freeze) 제거는 기본 OFF. SSIM 단독으로는 강의/화면녹화 등 정적 콘텐츠를
    # "정지 화면"으로 오판해 영상 대부분을 잘라낸다. 필요한 사용자만 켠다.
    remove_freeze: bool = False
    # 반복 테이크/말 더듬(같은 말 여러 번 다시 함) 자동 제거. 기본 ON.
    remove_retakes: bool = True
    model_size: str = "medium"   # 한국어 정확도↑ (base 는 오인식 많음)
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
            keep_padding_ms=params.keep_padding_ms,
        )

        await _emit(job, "freeze", 0.35)
        # 기본 OFF: 정적 콘텐츠 과다 컷 방지. 켠 경우에만 비용이 큰 프레임 분석 수행.
        if params.remove_freeze:
            freeze = await asyncio.to_thread(
                freeze_detector.detect_freeze,
                project.source_path,
                ssim_thresh=params.ssim_thresh,
                min_freeze_ms=params.min_freeze_ms,
            )
        else:
            freeze = []

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

        # 발화 단위 반복 테이크(false start) 감지 — 마지막 완성 테이크만 남김
        if params.remove_retakes:
            utterances = subtitle_remap.parse_srt(srt)
            retake = retake_detector.detect_retakes(utterances)
        else:
            retake = []

        await _emit(job, "plan", 0.9)
        segments = cut_planner.plan_keep_segments(
            project.duration, silence, freeze, stutter, retake,
        )

        project.detected = DetectedRegions(
            silence=silence, freeze=freeze, stutter=stutter, retake=retake,
        )
        project.segments = segments
        project.subtitle_srt_path = srt
        store.save(project)

        await _emit(job, "done", 1.0)
    except Exception as exc:  # 진행률 채널로 에러 전파
        await job.queue.put({"stage": "error", "progress": 0.0, "detail": str(exc)})
    finally:
        job.done = True
