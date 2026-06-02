"""파일 기반 store (Design 2 / V1 DB 없음).

store/{project_id}/project.json  — 프로젝트 메타
store/{project_id}/source.mp4    — 원본
store/{project_id}/subtitle.srt  — 자막
store/{project_id}/frames/       — 미리보기 캐시(선택)
"""
from __future__ import annotations

from pathlib import Path

from .models.project import Project

STORE_ROOT = Path(__file__).resolve().parent.parent / "store"


def project_dir(project_id: str) -> Path:
    d = STORE_ROOT / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _project_json(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def save(project: Project) -> None:
    path = _project_json(project.id)
    path.write_text(project.model_dump_json(indent=2), encoding="utf-8")


def load(project_id: str) -> Project | None:
    path = _project_json(project_id)
    if not path.exists():
        return None
    return Project.model_validate_json(path.read_text(encoding="utf-8"))


def exists(project_id: str) -> bool:
    return _project_json(project_id).exists()
