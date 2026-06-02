"""CapCut 草稿 폴더 자동 탐지 (FR-10 보조)."""
from __future__ import annotations

from fastapi import APIRouter

from ..services.capcut_locator import detect_draft_folder

router = APIRouter(prefix="/capcut", tags=["capcut"])


@router.get("/draft-folder")
async def draft_folder() -> dict:
    """OS별 표준 위치에서 com.lveditor.draft 폴더를 추정해 반환."""
    return detect_draft_folder()
