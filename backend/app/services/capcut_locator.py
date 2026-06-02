"""CapCut 草稿(draft) 폴더 자동 탐지 (FR-10 보조).

OS별 표준 위치의 `User Data/Projects/com.lveditor.draft` 경로를 추정한다.
CapCut(글로벌) / JianyingPro(중국판) 양쪽을 후보로 둔다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# DraftFolder 가 받는 부모 폴더: 모든 드래프트가 모이는 com.lveditor.draft
_DRAFT_SUBPATH = Path("User Data") / "Projects" / "com.lveditor.draft"


def _candidates() -> list[Path]:
    home = Path.home()
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return [
            local / "CapCut" / _DRAFT_SUBPATH,
            local / "JianyingPro" / _DRAFT_SUBPATH,
        ]
    if sys.platform == "darwin":
        appsup = home / "Library" / "Application Support"
        return [
            appsup / "CapCut" / _DRAFT_SUBPATH,
            home / "Movies" / "JianyingPro" / _DRAFT_SUBPATH,
        ]
    # Linux 등: CapCut 네이티브 빌드 없음 — 홈 기준 best-effort 후보만 제공
    return [home / "CapCut" / _DRAFT_SUBPATH]


def detect_draft_folder() -> dict:
    """탐지 결과. 실제 존재하는 첫 후보를 path 로, 없으면 첫 후보를 힌트로 반환."""
    cands = _candidates()
    existing = next((c for c in cands if c.is_dir()), None)
    chosen = existing or (cands[0] if cands else None)
    return {
        "path": str(chosen) if chosen else None,
        "exists": existing is not None,
        "candidates": [str(c) for c in cands],
    }
