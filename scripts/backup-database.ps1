param([string]$Database = 'mri_db')
$ErrorActionPreference = 'Stop'
if ($Database -notmatch '^mri_[a-z0-9_]+$') { throw 'Expected an MRI database name.' }
Set-Location (Split-Path $PSScriptRoot -Parent)
$name = "$Database-$(Get-Date -Format yyyyMMdd-HHmmss).dump"
New-Item -ItemType Directory -Force .backups | Out-Null
docker compose exec -T db pg_dump -U mri_user -d $Database -Fc -f "/tmp/$name"
if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed' }
docker compose cp "db:/tmp/$name" ".backups/$name"
if ($LASTEXITCODE -ne 0) { throw 'Backup copy failed' }
Get-FileHash -Algorithm SHA256 ".backups/$name"
