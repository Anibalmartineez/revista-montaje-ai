param([switch]$Restart)

$ErrorActionPreference = 'Stop'
$repo = (& git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Run from the repository.' }
Set-Location -LiteralPath $repo

if ($Restart) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\stop_flask.ps1
    if ($LASTEXITCODE -ne 0) { throw 'The registered Flask process could not be safely stopped.' }
}

$flags = @{
    EDITOR_OFFSET_V2_PREVIEW_ENABLED = '1'
    EDITOR_OFFSET_V2_PDF_FINAL_ENABLED = '1'
    EDITOR_OFFSET_V2_DERIVED_ASSETS_ENABLED = '0'
}
$previous = @{}
try {
    foreach ($name in $flags.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $flags[$name], 'Process')
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\editor-offset-local-qa\scripts\start_flask.ps1 -Target v2
    if ($LASTEXITCODE -ne 0) { throw 'Flask startup failed.' }
    & venv\Scripts\python.exe .agents\skills\editor-offset-local-qa\scripts\check_flask.py --target v2
    if ($LASTEXITCODE -ne 0) { throw 'HTTP verification failed.' }
    & venv\Scripts\python.exe scripts\check_editor_offset_v2_start.py
    if ($LASTEXITCODE -ne 0) { throw 'V2 output availability differs from the normal profile. Use -Restart for the registered process.' }
} finally {
    foreach ($name in $flags.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
}
