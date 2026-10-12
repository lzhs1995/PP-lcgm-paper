# Round2F 本机执行脚本（SD 分支）。逐步运行，任一步失败立即停止并保留现场；可按步骤单独重跑（全部步骤幂等）。
# 用法（PowerShell）：
#   Set-ExecutionPolicy -Scope Process Bypass
#   & 'C:\Users\LZHS\pp_lgcm_review\round2F_20261010\run_round2F.ps1' -Step all
# 步骤：setup → selftest → p0 → smoke → queue → pool → power；最后单独运行 export 生成回传包。
param([ValidateSet('setup', 'selftest', 'p0', 'smoke', 'queue', 'pool', 'power', 'export', 'all')][string]$Step = 'all')
$ErrorActionPreference = 'Stop'
$Root = 'C:/Users/LZHS/pp_lgcm_review/round2F_20261010'
$env:R2F_ROOT = $Root
$env:R2F_R2E = 'C:/Users/LZHS/pp_lgcm_review/round2E_20261010'
$env:R2F_R2D = 'C:/Users/LZHS/pp_lgcm_review/round2D_20261008'
$env:R2F_R2C = 'C:/Users/LZHS/pp_lgcm_review/round2C_20261007'
$env:R2F_PY = 'C:/Users/LZHS/AppData/Local/Programs/Python/Python314/python.exe'
$env:R2F_MPLUS = 'C:/Users/LZHS/Downloads/Mplus/mplus9/ducument/Mplus.exe'
$Rscript = 'C:/Users/LZHS/Downloads/RStudio/R_ducument/R-4.5.2/bin/Rscript.exe'

function Invoke-R([string]$Script) {
    Write-Output ('== ' + $Script + ' ' + (Get-Date).ToUniversalTime().ToString('o'))
    & $Rscript (Join-Path $Root ('code/' + $Script))
    if ($LASTEXITCODE -ne 0) { throw ($Script + ' failed with exit code ' + $LASTEXITCODE) }
}
function Read-Json([string]$Rel) {
    $f = Join-Path $Root $Rel
    if (-not (Test-Path $f)) { throw ('missing ' + $Rel) }
    Get-Content -Raw -Encoding UTF8 $f | ConvertFrom-Json
}
function Start-KeepAwake {
    $flag = Join-Path $Root 'runtime/KEEP_AWAKE_STOP'
    if (Test-Path $flag) { Remove-Item $flag }
    $argList = @((Join-Path $Root 'code/r2f_keep_awake.py'), $Root, "$PID")
    Start-Process -FilePath $env:R2F_PY -ArgumentList $argList -WindowStyle Hidden -PassThru
}
function Stop-KeepAwake($Proc) {
    Set-Content -Path (Join-Path $Root 'runtime/KEEP_AWAKE_STOP') -Value 'stop'
    if ($Proc) { $null = $Proc.WaitForExit(30000) }
}

function Step-Setup { Invoke-R 'r2f_setup.R' }
function Step-Selftest {
    Invoke-R 'r2f_selftest.R'
    $bad = @(Import-Csv (Join-Path $Root 'audit/SELFTEST_2F.csv') | Where-Object { $_.result -match 'FAIL|ERROR|SKIPPED' })
    if ($bad.Count -gt 0) { throw ('selftest not clean: ' + (($bad | ForEach-Object { $_.test }) -join ', ')) }
}
function Step-P0 {
    Invoke-R 'r2f_p0.R'
    if (-not (Read-Json 'audit/P0_STATUS_2F.json').passed) { throw 'P0 failed; see audit/P0_CHECKS_2F.csv' }
}
function Step-Smoke {
    Invoke-R 'r2f_smoke.R'
    if (-not (Read-Json 'audit/SMOKE_2F.json').passed) { throw 'smoke failed; see audit/SMOKE_CHECKS_2F.csv' }
}
function Step-Queue { Invoke-R 'r2f_queue.R' }
function Step-Pool { Invoke-R 'r2f_pool.R' }
function Step-Export {
    $out = 'C:/Users/LZHS/pp_lgcm_review/round2F_return.zip'
    & $env:R2F_PY -I (Join-Path $Root 'code/r2f_export.py') $Root $out (Join-Path $Root 'code')
    if ($LASTEXITCODE -ne 0) { throw ('export failed with exit code ' + $LASTEXITCODE) }
}
function Step-Power {
    $w = Read-Json 'runtime/batch_window.json'
    & (Join-Path $Root 'record_power_events_window.ps1') -StartUtc $w.start_utc -Out (Join-Path $Root 'audit/SYSTEM_POWER_EVENTS_2F.json')
}

$keep = $null
try {
    if ($Step -in @('p0', 'smoke', 'queue', 'all')) { $keep = Start-KeepAwake }
    switch ($Step) {
        'setup' { Step-Setup }
        'selftest' { Step-Selftest }
        'p0' { Step-P0 }
        'smoke' { Step-Smoke }
        'queue' { Step-Queue }
        'pool' { Step-Pool }
        'power' { Step-Power }
        'export' { Step-Export }
        'all' { Step-Setup; Step-Selftest; Step-P0; Step-Smoke; Step-Queue; Step-Pool }
    }
}
finally {
    if ($keep) { Stop-KeepAwake $keep }
    if ($Step -eq 'all' -and (Test-Path (Join-Path $Root 'runtime/batch_window.json'))) { Step-Power }
}
Write-Output ('ROUND2F_STEP_DONE ' + $Step)
