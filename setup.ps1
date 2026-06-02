<#
  CapCut 자동편집 — 원클릭 세팅 (Windows)

  사용자가 "프로그램 세팅해줘"라고 하면 Claude 가 이 스크립트를 실행한다.
  멱등(idempotent): 여러 번 돌려도 안전하며 이미 된 단계는 건너뛴다.

  하는 일:
    1) ffmpeg 설치(winget) 및 경로 확인
    2) 백엔드 Python venv 생성 + 의존성 설치
    3) 프론트엔드 npm 의존성 설치
    4) CapCut 草稿(draft) 저장 폴더를 이 컴퓨터 기준으로 탐지/검증
    5) (옵션) Whisper medium 모델 사전 다운로드

  실행:  powershell -ExecutionPolicy Bypass -File setup.ps1 [-SkipModel]
#>
param(
  [switch]$SkipModel  # 지정 시 Whisper 모델 사전 다운로드 생략
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Write-Host "=== CapCut 자동편집 세팅 시작 ===" -ForegroundColor Cyan

# ---------------------------------------------------------------- 1) ffmpeg
function Find-Ffmpeg {
  $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $pkg = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($pkg) { return $pkg.FullName }
  return $null
}

$ff = Find-Ffmpeg
if (-not $ff) {
  Write-Host "[1/5] ffmpeg 미설치 → winget 설치 중..." -ForegroundColor Yellow
  winget install --id Gyan.FFmpeg -e --source winget --accept-source-agreements --accept-package-agreements --disable-interactivity
  $ff = Find-Ffmpeg
}
if (-not $ff) { throw "ffmpeg 설치 실패. 수동 설치 후 다시 실행하세요." }
$ffDir = Split-Path $ff
$env:PATH = "$ffDir;$env:PATH"   # 현재 세션에 즉시 반영
Write-Host "[1/5] ffmpeg OK: $ff" -ForegroundColor Green

# ---------------------------------------------------- 2) 백엔드 venv + deps
$venvPy = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "[2/5] 백엔드 venv 생성..." -ForegroundColor Yellow
  & py -m venv (Join-Path $root "backend\.venv")
}
Write-Host "[2/5] 백엔드 의존성 설치..." -ForegroundColor Yellow
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r (Join-Path $root "backend\requirements.txt") --quiet
Write-Host "[2/5] 백엔드 의존성 OK" -ForegroundColor Green

# ------------------------------------------------------ 3) 프론트엔드 deps
Write-Host "[3/5] 프론트엔드 의존성 설치 (npm install)..." -ForegroundColor Yellow
Push-Location (Join-Path $root "frontend")
try { npm install } finally { Pop-Location }
Write-Host "[3/5] 프론트엔드 의존성 OK" -ForegroundColor Green

# ------------------------------------------- 4) CapCut 草稿 폴더 탐지/검증
# capcut_locator 와 동일한 OS 표준 경로를 검사한다.
$draftSub = "User Data\Projects\com.lveditor.draft"
$candidates = @(
  (Join-Path $env:LOCALAPPDATA "CapCut\$draftSub"),
  (Join-Path $env:LOCALAPPDATA "JianyingPro\$draftSub")
)
$capcut = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($capcut) {
  Write-Host "[4/5] CapCut 草稿 폴더 발견: $capcut" -ForegroundColor Green
} else {
  Write-Host "[4/5] CapCut 草稿 폴더를 못 찾음. CapCut 설치 후 한 번 실행하면 생성됩니다." -ForegroundColor Yellow
  Write-Host "      (앱 실행 중엔 '드래프트 생성' 화면이 경로를 자동으로 채웁니다.)"
}

# --------------------------------------- 5) (옵션) Whisper medium 사전 다운로드
if ($SkipModel) {
  Write-Host "[5/5] 모델 사전 다운로드 생략(-SkipModel). 첫 분석 시 자동 다운로드됩니다." -ForegroundColor Yellow
} else {
  Write-Host "[5/5] Whisper medium 모델 사전 다운로드(~1.5GB, 시간 소요)..." -ForegroundColor Yellow
  & $venvPy -c "import os; os.environ.setdefault('HF_HUB_DISABLE_XET','1'); from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8'); print('model ready')"
  Write-Host "[5/5] 모델 준비 완료" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== 세팅 완료 ===" -ForegroundColor Cyan
Write-Host "서버 실행:" -ForegroundColor Cyan
Write-Host "  백엔드 : cd backend; `$env:PATH='$ffDir;'+`$env:PATH; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
Write-Host "  프론트 : cd frontend; npm run dev   (http://localhost:5173)"
