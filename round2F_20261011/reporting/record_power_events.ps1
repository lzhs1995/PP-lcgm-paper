# 只读取本批时间窗口内系统电源事件；不改变电源计划。
$ErrorActionPreference='Stop'
$eventRoot=Split-Path $PSScriptRoot -Parent
$eventBatch=Get-Content (Join-Path $eventRoot 'runtime/batch_window.json') -Raw | ConvertFrom-Json
$eventStart=[DateTime]::Parse($eventBatch.start_utc).ToLocalTime()
$eventEnd=Get-Date
$eventRows=@(Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$eventStart; EndTime=$eventEnd; Id=1,42,107,506,507} -ErrorAction SilentlyContinue |
    Where-Object {$_.ProviderName -in @('Microsoft-Windows-Kernel-Power','Microsoft-Windows-Power-Troubleshooter')} |
    ForEach-Object {
        [PSCustomObject]@{utc=$_.TimeCreated.ToUniversalTime().ToString('o'); id=$_.Id; provider=$_.ProviderName; message=$_.Message}
    })
$eventRecord=[PSCustomObject]@{status='READ_COMPLETE'; start_utc=$eventBatch.start_utc; end_utc=$eventEnd.ToUniversalTime().ToString('o'); events=$eventRows}
$eventOutput=Join-Path $eventRoot 'audit/SYSTEM_POWER_EVENTS_2F.json'
[IO.File]::WriteAllText($eventOutput,(ConvertTo-Json -InputObject $eventRecord -Depth 5),(New-Object Text.UTF8Encoding($false)))
Write-Output ('POWER_EVENTS_SAVED '+$eventRows.Count)
