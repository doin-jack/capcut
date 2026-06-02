"""프로젝트 CRUD + 업로드 (Design 4 / FR-01)."""
from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import store
from ..models.project import Project
from ..services.media_meta import extract_meta

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("")
async def create_project(file: UploadFile = File(...), name: str = Form(...)) -> Project:
    project_id = uuid.uuid4().hex[:12]
    pdir = store.project_dir(project_id)
    ext = (file.filename or "source.mp4").rsplit(".", 1)[-1]
    source_path = pdir / f"source.{ext}"

    with source_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    meta = extract_meta(str(source_path))
    project = Project(
        id=project_id,
        name=name,
        source_path=str(source_path),
        duration=meta["duration"],
        fps=meta["fps"],
        width=meta["width"],
        height=meta["height"],
    )
    store.save(project)
    return project


@router.get("/{project_id}")
async def get_project(project_id: str) -> Project:
    project = store.load(project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    return project
