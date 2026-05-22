param(
  [switch]$SkipBackend,
  [switch]$SkipFrontend,
  [switch]$SkipSecrets
)

$ErrorActionPreference = "Stop"

function Require-Command {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [Parameter(Mandatory = $true)]
    [string]$InstallHint
  )

  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing required command '$Name'. $InstallHint"
  }
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

Write-Host "CorrelCore local quality gate"
Write-Host "Repository: $RepoRoot"

Require-Command "git" "Install Git for Windows and reopen PowerShell."

if (-not $SkipFrontend) {
  Require-Command "pnpm.CMD" "Install Node 22 and enable Corepack, or install pnpm 11.0.8."

  Write-Host ""
  Write-Host "Frontend: install, lint, typecheck, test"
  & pnpm.CMD install --frozen-lockfile
  & pnpm.CMD --filter "@correlcore/web" lint
  & pnpm.CMD --filter "@correlcore/web" typecheck
  & pnpm.CMD --filter "@correlcore/web" test
}

if (-not $SkipBackend) {
  Require-Command "uv" "Install with: winget install astral-sh.uv"

  Write-Host ""
  Write-Host "Backend: sync, lint, format check, typecheck, tests"
  Push-Location (Join-Path $RepoRoot "backend")
  try {
    & uv sync --python 3.12 --extra dev --extra analytics --frozen
    & uv run --python 3.12 ruff check .
    & uv run --python 3.12 ruff format --check .
    & uv run --python 3.12 mypy app
    & uv run --python 3.12 pytest
  } finally {
    Pop-Location
  }
}

if (-not $SkipSecrets) {
  Require-Command "gitleaks" "Install with: winget install gitleaks.gitleaks"

  Write-Host ""
  Write-Host "Secrets: working tree and Git history"
  & gitleaks detect --source . --no-git --redact
  & gitleaks detect --source . --redact
}

Write-Host ""
Write-Host "Local quality gate completed."
