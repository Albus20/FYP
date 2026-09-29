# Commit and push the current working-tree changes.
# Idempotent. ASCII only. Handles CJK filenames.
# NOTE: ErrorActionPreference is Continue on purpose - git writes normal
# informational output to stderr, which Stop would treat as fatal.
#
# Usage (the commit message is REQUIRED - describe what this commit changes):
#   .\sync.ps1 -Message "J3/J4-2 ingested; RQ1 robustness check"
#   .\sync.ps1 -Message "short summary" -Body "- detail 1`n- detail 2"
# Chinese in the message is fine: it is written to a UTF-8 file and passed
# to git with -F, so it is not garbled by the console code page.
# (2026-09-29: the message used to be hard-coded, which is why commits from
#  09-22 to 09-28 all carried the same "W3: log Jia's J1 return..." text.)

param(
    [Parameter(Mandatory = $true)][string]$Message,
    [string]$Body = ""
)

$ErrorActionPreference = "Continue"
if ([string]::IsNullOrWhiteSpace($Message)) {
    Write-Host "STOP: commit message is empty." -ForegroundColor Red
    exit 1
}
Set-Location "C:\FYP\data_repo"

git config core.quotepath false
$prevEnc = [Console]::OutputEncoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "[1/4] Changes to commit:" -ForegroundColor Cyan
git add -A
$staged = @(git diff --cached --name-only)
if ($staged.Count -eq 0) {
    Write-Host "  nothing to commit - working tree clean"
    [Console]::OutputEncoding = $prevEnc
    exit 0
}
$staged | ForEach-Object { Write-Host "    $_" }

Write-Host ""
Write-Host "[2/4] SAFETY CHECK..." -ForegroundColor Cyan
$danger = $staged | Where-Object {
    $_ -match "(^|/)\.keys\.env$"               -or
    $_ -match "^raw/openalex_author_inst_years" -or
    $_ -match "^raw/openalex_author_quarters"   -or
    $_ -match "^raw/openalex_works_master"      -or
    $_ -match "^raw/_ckpt_"                     -or
    $_ -match "^raw/_archive/"                  -or
    $_ -match "(^|/)__pycache__/"
}
if ($danger) {
    Write-Host "  STOP: these must not be committed:" -ForegroundColor Red
    $danger | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    git reset | Out-Null
    [Console]::OutputEncoding = $prevEnc
    exit 1
}
$big = @()
foreach ($f in $staged) {
    $item = Get-Item -LiteralPath $f -ErrorAction SilentlyContinue
    if ($item -and $item.Length -gt 5MB) {
        $big += ("{0}  ({1} MB)" -f $f, [math]::Round($item.Length/1MB,1))
    }
}
if ($big.Count -gt 0) {
    Write-Host "  STOP: file(s) over 5 MB:" -ForegroundColor Red
    $big | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    git reset | Out-Null
    [Console]::OutputEncoding = $prevEnc
    exit 1
}
Write-Host "  OK"

Write-Host ""
Write-Host "[3/4] Commit..." -ForegroundColor Cyan
$msg = $Message.Trim()
if (-not [string]::IsNullOrWhiteSpace($Body)) { $msg = $msg + [char]10 + [char]10 + $Body.Trim() }
$msgFile = Join-Path $env:TEMP ("fyp_commit_msg_{0}.txt" -f [guid]::NewGuid())
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding $false))
git -c user.name="TaricQiu" -c user.email="taricqiu@gmail.com" -c i18n.commitEncoding=utf-8 commit -F $msgFile
$commitExit = $LASTEXITCODE
Remove-Item -LiteralPath $msgFile -ErrorAction SilentlyContinue
if ($commitExit -ne 0) {
    Write-Host "STOP: commit failed (exit $commitExit). Nothing was pushed." -ForegroundColor Red
    [Console]::OutputEncoding = $prevEnc
    exit 1
}

Write-Host ""
Write-Host "[4/4] Push..." -ForegroundColor Cyan
git push

[Console]::OutputEncoding = $prevEnc

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "DONE: https://github.com/Qiuu2/FYP" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Push failed. If remote is ahead:" -ForegroundColor Yellow
    Write-Host "  git pull --rebase origin main" -ForegroundColor White
    Write-Host "  git push" -ForegroundColor White
}
