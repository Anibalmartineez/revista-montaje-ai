param([switch]$Restart)
$ErrorActionPreference = 'Stop'
$repo = (& git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Run from the repository.' }
Set-Location -LiteralPath $repo
if ($Restart) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\stop_flask.ps1
    if ($LASTEXITCODE -ne 0) { throw 'The registered Flask process could not be safely stopped.' }
}
$names = @('EDITOR_OFFSET_V2_PREVIEW_ENABLED','EDITOR_OFFSET_V2_PDF_FINAL_ENABLED','EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED')
$previous = @{}
try {
    foreach ($name in $names) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
        [Environment]::SetEnvironmentVariable($name,'1','Process')
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\start_flask.ps1 -Target v2
    if ($LASTEXITCODE -ne 0) { throw 'Flask startup failed.' }
    & venv\Scripts\python.exe .agents\skills\editor-offset-local-qa\scripts\check_flask.py --target v2
    if ($LASTEXITCODE -ne 0) { throw 'HTTP verification failed.' }
    & venv\Scripts\python.exe scripts\check_editor_offset_v2_output_qa.py
    if ($LASTEXITCODE -ne 0) { throw 'Output gates are not active; use -Restart for the registered process.' }
    Write-Output 'V2 output QA requested. An already-running process keeps its original flags; use -Restart for the registered process. Dev tools remain disabled.'
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
