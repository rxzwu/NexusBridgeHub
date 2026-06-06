# Verify NexusBridge on Python 3.11–3.14 (one venv at a time, no lock contention).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$versions = @("3.11", "3.12", "3.13", "3.14")
$results = @()

foreach ($v in $versions) {
    $venv = ".tmp-pytest-$($v.Replace('.', ''))"
    if (Test-Path $venv) {
        Remove-Item -Recurse -Force $venv
    }

    Write-Host ""
    Write-Host "=== Python $v ===" -ForegroundColor Cyan

    uv venv $venv --python $v
    $py = Join-Path (Resolve-Path $venv) "Scripts\python.exe"

    Write-Host "Installing dependencies..."
    uv pip install -e ".[dev]" --python $py

    Write-Host "Running tests..."
    & $py -m pytest tests/ -q
    if ($LASTEXITCODE -eq 0) {
        $results += "$v PASS"
        Write-Host "$v PASS" -ForegroundColor Green
    } else {
        $results += "$v FAIL (exit $LASTEXITCODE)"
        Write-Host "$v FAIL (exit $LASTEXITCODE)" -ForegroundColor Red
    }

    Remove-Item -Recurse -Force $venv
}

Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Cyan
foreach ($line in $results) {
    if ($line -match "PASS") {
        Write-Host $line -ForegroundColor Green
    } else {
        Write-Host $line -ForegroundColor Red
        exit 1
    }
}
