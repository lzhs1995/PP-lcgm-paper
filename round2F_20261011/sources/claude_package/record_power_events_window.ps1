# 只读电源事件记录（Kernel-Power / Power-Troubleshooter：1、42、107、506、507），按批次窗口截取。
# 用法：record_power_events_window.ps1 -StartUtc 2026-10-11T01:00:00Z [-EndUtc ...] -Out <json>
param([Parameter(Mandatory = $true)][string]$StartUtc, [string]$EndUtc = '', [Parameter(Mandatory = $true)][string]$Out)
$ErrorActionPreference = 'Stop'
$start = [DateTime]::Parse($StartUtc).ToUniversalTime().ToLocalTime()
if ($EndUtc) { $end = [DateTime]::Parse($EndUtc).ToUniversalTime().ToLocalTime() } else { $end = Get-Date }
$rows = @(Get-WinEvent -FilterHashtable @{LogName = 'System'; StartTime = $start; EndTime = $end; Id = 1, 42, 107, 506, 507} -ErrorAction SilentlyContinue |
    Where-Object { $_.ProviderName -in @('Microsoft-Windows-Kernel-Power', 'Microsoft-Windows-Power-Troubleshooter') } |
    ForEach-Object { [PSCustomObject]@{ utc = $_.TimeCreated.ToUniversalTime().ToString('o'); id = $_.Id; provider = $_.ProviderName; message = $_.Message } })
$doc = [PSCustomObject]@{ window_start_utc = $StartUtc; window_end_utc = $end.ToUniversalTime().ToString('o'); event_count = $rows.Count; events = $rows }
[IO.File]::WriteAllText($Out, ($doc | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding($false)))
Write-Output ('POWER_EVENTS_SAVED ' + $rows.Count)
