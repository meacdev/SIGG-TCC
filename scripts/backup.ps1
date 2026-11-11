param(
    [Parameter(Mandatory=$true)][string]$Database,
    [string]$HostName = 'localhost',
    [int]$Port = 5432,
    [Parameter(Mandatory=$true)][string]$UserName,
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\backups'),
    [string]$PgDump = 'pg_dump'
)
$ErrorActionPreference = 'Stop'
# Configure PGPASSFILE / pgpass.conf. No password is passed in the command line.
$null = New-Item -ItemType Directory -Path $OutputDirectory -Force
$target = Join-Path (Resolve-Path -LiteralPath $OutputDirectory).Path (
    'sigg_tcc_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.dump'
)
& $PgDump --host=$HostName --port=$Port --username=$UserName --dbname=$Database `
    --format=custom --no-password --file=$target
if ($LASTEXITCODE -ne 0) { throw 'pg_dump falhou. Verifique conexão e PGPASSFILE.' }
Get-FileHash -LiteralPath $target -Algorithm SHA256 | Format-List
