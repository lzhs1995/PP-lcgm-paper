# Read-only power-event evidence; exclude host and user identifiers.
$ErrorActionPreference='Stop'
$eventStart=[DateTime]::Parse('2026-10-10T03:50:00Z').ToLocalTime()
$eventRows=@(Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$eventStart; Id=1,42,107,506,507} -ErrorAction SilentlyContinue |
    Where-Object {$_.ProviderName -in @('Microsoft-Windows-Kernel-Power','Microsoft-Windows-Power-Troubleshooter')} |
    ForEach-Object {
        [PSCustomObject]@{utc=$_.TimeCreated.ToUniversalTime().ToString('o'); id=$_.Id; provider=$_.ProviderName; message=$_.Message}
    })
$eventOutput=Join-Path $PSScriptRoot '../audit/SYSTEM_POWER_EVENTS.json'
[IO.File]::WriteAllText($eventOutput,($eventRows | ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
Write-Output ('POWER_EVENTS_SAVED '+$eventRows.Count)
