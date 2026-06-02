"""드래프트 엔드포인트 에러 처리 (CapCut 잠금 등) 테스트.

build_draft 가 PermissionError 를 던지면(=대상 드래프트가 CapCut에서 열려 잠김)
500/Network Error 가 아니라 명확한 409 메시지를 반환해야 한다.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

import app.api.editing as editing
from app.main import app
from app.models.project import Project

client = TestClient(app)


def _dummy_project() -> Project:
    return Project(id="p1", name="demo", source_path="x.mp4")


def test_draft_locked_returns_409(monkeypatch):
    monkeypatch.setattr(editing.store, "load", lambda pid: _dummy_project())
    monkeypatch.setattr(editing.store, "save", lambda p: None)

    def _boom(project, folder, name=None):
        raise PermissionError("[WinError 32] .locked")

    monkeypatch.setattr(editing, "build_draft", _boom)

    r = client.post("/projects/p1/draft", json={"draft_folder": "/tmp/x"})
    assert r.status_code == 409
    assert "CapCut" in r.json()["detail"]


def test_draft_unknown_error_returns_500_with_detail(monkeypatch):
    monkeypatch.setattr(editing.store, "load", lambda pid: _dummy_project())
    monkeypatch.setattr(editing.store, "save", lambda p: None)

    def _boom(project, folder, name=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(editing, "build_draft", _boom)

    r = client.post("/projects/p1/draft", json={"draft_folder": "/tmp/x"})
    assert r.status_code == 500
    assert "boom" in r.json()["detail"]


def test_draft_missing_project_returns_404(monkeypatch):
    monkeypatch.setattr(editing.store, "load", lambda pid: None)
    r = client.post("/projects/nope/draft", json={"draft_folder": "/tmp/x"})
    assert r.status_code == 404
