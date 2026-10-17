param([string]$Phase = 'final', [switch]$SkipApk)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$env:DEBUG = 'false'
if (!$env:DATABASE_URL) { $env:DATABASE_URL = 'postgresql+psycopg://mri_user:mri_password@127.0.0.1:55433/mri_release' }
$out = Join-Path $root "docs/verification/$Phase"
New-Item -ItemType Directory -Force $out | Out-Null
$results = @()
function Check($name, $directory, $program, $arguments) {
    Push-Location $directory
    try {
        $ErrorActionPreference = 'Continue'
        & $program @arguments *> (Join-Path $out "$name.log")
        $script:results += [pscustomobject]@{ check=$name; exit_code=$LASTEXITCODE; utc=[DateTime]::UtcNow.ToString('o') }
        Write-Host "$name exit=$LASTEXITCODE"
    } finally { Pop-Location }
}
Check 'python' $root "$root/.venv/Scripts/python.exe" @('-u','-m','pytest','backend/tests','ml/tests','-q','--tb=short','-o','faulthandler_timeout=30')
Check 'web-tests' "$root/frontend-web" 'npm.cmd' @('test')
Check 'web-build' "$root/frontend-web" 'npm.cmd' @('run','build')
Check 'web-lint' "$root/frontend-web" 'npm.cmd' @('run','lint')
Check 'pub-get' "$root/mobile" 'flutter.bat' @('pub','get')
Check 'format' "$root/mobile" 'dart.bat' @('format','--output=none','--set-exit-if-changed','.')
Check 'analyze' "$root/mobile" 'flutter.bat' @('analyze')
Check 'flutter-tests' "$root/mobile" 'flutter.bat' @('test')
if (!$SkipApk) { Check 'apk' "$root/mobile" 'flutter.bat' @('build','apk','--debug') }
$results | ConvertTo-Json | Set-Content (Join-Path $out 'results.json')
if ($results.exit_code | Where-Object { $_ -ne 0 }) { exit 1 }
