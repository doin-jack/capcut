"""분석 시작 + WS 진행률 (Design 4 /analyze)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .. import store
from ..analysis_runner import AnalyzeParams, get_job, run_analysis

router = APIRouter(prefix="/projects", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    min_silence_ms: int = 700
    silence_thresh_db: float = -40.0
    keep_padding_ms: int = 200   # 무음 양끝 여유(숨 쉬는 간격). 클수록 덜 급함
    ssim_thresh: float = 0.985
    min_freeze_ms: int = 500
    remove_freeze: bool = False   # 멈춤 제거 기본 OFF (정적 콘텐츠 과다 컷 방지)
    remove_retakes: bool = True   # 반복 테이크/말더듬 제거 기본 ON
    model_size: str = "medium"    # 한국어 정확도↑
    language: str | None = None


@router.post("/{project_id}/analyze", status_code=202)
async def start_analyze(project_id: str, req: AnalyzeRequest) -> dict:
    if not store.exists(project_id):
        raise HTTPException(404, "project not found")
    params = AnalyzeParams(**req.model_dump())
    asyncio.create_task(run_analysis(project_id, params))
    return {"job_id": project_id, "status": "started"}


@router.websocket("/{project_id}/analyze/ws")
async def analyze_ws(websocket: WebSocket, project_id: str) -> None:
    await websocket.accept()
    # job 시작 직후 접속을 허용하기 위해 잠시 대기 폴링
    for _ in range(50):
        job = get_job(project_id)
        if job is not None:
            break
        await asyncio.sleep(0.1)
    else:
        await websocket.send_json({"stage": "error", "progress": 0.0, "detail": "no job"})
        await websocket.close()
        return

    try:
        while True:
            msg = await job.queue.get()
            await websocket.send_json(msg)
            if msg["stage"] in ("done", "error"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
