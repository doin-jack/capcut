"""세그먼트/미리보기/드래프트 (Design 4 / FR-06,08,09,10)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .. import store
from ..models.clip_props import ClipProps
from ..models.project import Segment
from ..services.draft_builder import build_draft
from ..services.frame_preview import render_preview

router = APIRouter(prefix="/projects", tags=["editing"])


class SegmentPatch(BaseModel):
    """props 수정 또는 enabled 토글(FR-06). 둘 다 선택적."""

    props: ClipProps | None = None
    enabled: bool | None = None


class PreviewRequest(BaseModel):
    sid: str
    time: float                 # 원본 기준 초
    props: ClipProps = ClipProps()


class DraftRequest(BaseModel):
    draft_folder: str


@router.get("/{project_id}/segments")
async def list_segments(project_id: str) -> list[Segment]:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    return project.segments


@router.patch("/{project_id}/segments/{sid}")
async def patch_segment(project_id: str, sid: str, patch: SegmentPatch) -> Segment:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    seg = next((s for s in project.segments if s.id == sid), None)
    if seg is None:
        raise HTTPException(404, "segment not found")
    if patch.props is not None:
        seg.props = patch.props
    if patch.enabled is not None:
        seg.enabled = patch.enabled
    store.save(project)
    return seg


@router.post("/{project_id}/preview")
async def preview(project_id: str, req: PreviewRequest) -> Response:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    png = render_preview(project.source_path, req.time, req.props)
    return Response(content=png, media_type="image/png")


@router.post("/{project_id}/draft")
async def make_draft(project_id: str, req: DraftRequest) -> dict:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    draft_path = build_draft(project, req.draft_folder)
    project.capcut_draft_path = draft_path
    store.save(project)
    return {"draft_path": draft_path}
