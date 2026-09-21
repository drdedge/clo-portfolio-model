param(
    [Parameter(Mandatory=$true)][string]$Portfolio,
    [string]$Output = 'CLO_Model.xlsx',
    [string]$Config = '',
    [string]$AssumptionsFrom = '',
    [string]$FitchInputs = '',
    [switch]$ValidateOnly,
    [switch]$EngineOnly
)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython = (Get-Command python -ErrorAction Stop).Source
}
$taskPortfolio = (Resolve-Path -LiteralPath $Portfolio).Path
$taskOutput = [System.IO.Path]::GetFullPath($Output)
if ($Config -eq '') { $Config = Join-Path $taskRoot 'config\model.json' }
$taskConfig = (Resolve-Path -LiteralPath $Config).Path
$taskArgs = @('-m','clo','--portfolio',$taskPortfolio,'--config',$taskConfig,'--output',$taskOutput)
if ($AssumptionsFrom -ne '') { $taskArgs += @('--assumptions-from',(Resolve-Path -LiteralPath $AssumptionsFrom).Path) }
if ($FitchInputs -ne '') { $taskArgs += @('--fitch-inputs',(Resolve-Path -LiteralPath $FitchInputs).Path) }
if ($ValidateOnly) { $taskArgs += '--validate-only' }
if ($EngineOnly) { $taskArgs += '--engine-only' }
Push-Location -LiteralPath $taskRoot
try {
    & $taskPython @taskArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally { Pop-Location }
