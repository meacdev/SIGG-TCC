param(
    [Parameter(Mandatory=$true)][string]$Database,
    [Parameter(Mandatory=$true)][string]$UserName,
    [string]$PgDump = 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe',
    [string]$Time = '02:00'
)
$ErrorActionPreference = 'Stop'
# Run explicitly after configuring pgpass for the Windows account running the task.
$backupScript = Join-Path $PSScriptRoot 'backup.ps1'
foreach ($value in @($backupScript, $Database, $UserName, $PgDump)) {
    if ($value.Contains('"') -or $value.Contains("`n") -or $value.Contains("`r")) {
        throw 'Parâmetro inválido.'
    }
}
$arguments = '-NoProfile -File "' + $backupScript + '" -Database "' + $Database +
    '" -UserName "' + $UserName + '" -PgDump "' + $PgDump + '"'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
Register-ScheduledTask -TaskName 'SIGG-TCC Backup Diário' -Action $action -Trigger $trigger `
    -Description 'Backup PostgreSQL diário do SIGG-TCC' -ErrorAction Stop
