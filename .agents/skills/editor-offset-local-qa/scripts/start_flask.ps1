param(
    [ValidateSet("v1", "v2", "both")]
    [string]$Target = "v1",

    [switch]$EnableV2DevTools
)

$ErrorActionPreference = "Stop"
if (Test-Path Variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Get-RepositoryRoot {
    $rootOutput = @(& git rev-parse --show-toplevel 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo determinar la raíz Git: $($rootOutput -join ' ')"
    }
    $root = ($rootOutput | Select-Object -First 1).ToString().Trim()
    if ([string]::IsNullOrWhiteSpace($root)) {
        throw "git rev-parse --show-toplevel no devolvió una ruta."
    }
    return [System.IO.Path]::GetFullPath($root)
}

function Test-SavedProcessIsActive {
    param([string]$PidPath)

    if (-not (Test-Path -LiteralPath $PidPath -PathType Leaf)) {
        return $false
    }
    $savedPidText = (Get-Content -LiteralPath $PidPath -Raw).Trim()
    $savedPid = 0
    if (-not [int]::TryParse($savedPidText, [ref]$savedPid) -or $savedPid -le 0) {
        throw "El archivo PID existe pero no contiene un PID válido: $PidPath"
    }
    $savedProcess = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
    if ($null -ne $savedProcess) {
        Write-Output "Ya existe un proceso activo registrado por la Skill (PID $savedPid). No se iniciará otro."
        return $true
    }
    Remove-Item -LiteralPath $PidPath -Force
    Write-Output "Se eliminó únicamente el archivo PID obsoleto: $PidPath"
    return $false
}

$repoRoot = Get-RepositoryRoot
Set-Location -LiteralPath $repoRoot

$pythonPath = Join-Path $repoRoot "venv\Scripts\python.exe"
$entryPoint = Join-Path $repoRoot "app.py"
$checkScript = Join-Path $repoRoot ".agents\skills\editor-offset-local-qa\scripts\check_flask.py"
$runtimeDir = Join-Path $repoRoot ".codex-runtime\editor-offset-local-qa"
$pidPath = Join-Path $runtimeDir "flask.pid"
$metadataPath = Join-Path $runtimeDir "process.json"
$targetValue = $Target.ToLowerInvariant()

foreach ($requiredFile in @($pythonPath, $entryPoint, $checkScript)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "No existe el archivo requerido: $requiredFile"
    }
}

if ((Test-Path -LiteralPath $runtimeDir -PathType Container) -and (Test-SavedProcessIsActive -PidPath $pidPath)) {
    & $pythonPath $checkScript --target $targetValue --attempts 1 --interval 0 --timeout 2
    if ($LASTEXITCODE -eq 0) {
        Write-Output "El proceso registrado ya sirve el target '$targetValue'."
        exit 0
    }
    throw "Existe un proceso activo registrado por la Skill, pero no sirve el target '$targetValue'. Deténgalo con stop_flask.ps1 antes de cambiar de modo."
}

Write-Output "Comprobando si Flask ya responde para el target '$targetValue' antes de iniciar otro servidor..."
& $pythonPath $checkScript --target $targetValue --attempts 1 --interval 0 --timeout 2
if ($LASTEXITCODE -eq 0) {
    Write-Output "Flask ya responde en todas las rutas obligatorias del target '$targetValue'. No se iniciará otro proceso."
    exit 0
}

& $pythonPath $checkScript --target root --attempts 1 --interval 0 --timeout 2
if ($LASTEXITCODE -eq 0) {
    throw "Ya existe un servidor respondiendo en http://127.0.0.1:5000/, pero no sirve el target '$targetValue'. No se iniciará un proceso duplicado ni se ocupará el mismo puerto."
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$stdoutPath = Join-Path $runtimeDir "stdout-$timestamp.log"
$stderrPath = Join-Path $runtimeDir "stderr-$timestamp.log"

# Importar app.py sin ejecutar su bloque __main__ evita el reloader de Werkzeug y conserva un único PID controlable.
$bootstrapCode = "from app import app; skill_marker='editor-offset-local-qa'; app.run(debug=True, use_reloader=False)"
$bootstrapArgument = '"' + $bootstrapCode + '"'
$commandDisplay = '"{0}" -c "{1}"' -f $pythonPath, $bootstrapCode

$v2Enabled = if ($targetValue -in @("v2", "both")) { "1" } else { "0" }
$v2DevToolsEnabled = if ($v2Enabled -eq "1" -and $EnableV2DevTools) { "1" } else { "0" }
$previousV2Enabled = [Environment]::GetEnvironmentVariable("EDITOR_OFFSET_V2_ENABLED", "Process")
$previousV2DevToolsEnabled = [Environment]::GetEnvironmentVariable("EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED", "Process")
$startArguments = @{
    FilePath = $pythonPath
    ArgumentList = @("-c", $bootstrapArgument)
    WorkingDirectory = $repoRoot
    RedirectStandardOutput = $stdoutPath
    RedirectStandardError = $stderrPath
    WindowStyle = "Hidden"
    PassThru = $true
}

try {
    $env:EDITOR_OFFSET_V2_ENABLED = $v2Enabled
    $env:EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED = $v2DevToolsEnabled
    $process = Start-Process @startArguments
} finally {
    if ($null -eq $previousV2Enabled) {
        Remove-Item Env:\EDITOR_OFFSET_V2_ENABLED -ErrorAction SilentlyContinue
    } else {
        $env:EDITOR_OFFSET_V2_ENABLED = $previousV2Enabled
    }
    if ($null -eq $previousV2DevToolsEnabled) {
        Remove-Item Env:\EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED -ErrorAction SilentlyContinue
    } else {
        $env:EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED = $previousV2DevToolsEnabled
    }
}

$processStartUtc = $process.StartTime.ToUniversalTime().ToString("o")
$metadata = [ordered]@{
    schema_version = 2
    pid = $process.Id
    target = $targetValue
    editor_offset_v2_enabled = $v2Enabled
    editor_offset_v2_dev_tools_enabled = $v2DevToolsEnabled
    executable_path = $pythonPath
    entry_point = $entryPoint
    working_directory = $repoRoot
    process_start_time_utc = $processStartUtc
    recorded_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    command = $commandDisplay
    marker = "editor-offset-local-qa"
    stdout_path = $stdoutPath
    stderr_path = $stderrPath
}
$metadata | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $metadataPath -Encoding UTF8
$process.Id.ToString() | Set-Content -LiteralPath $pidPath -Encoding ASCII

Start-Sleep -Milliseconds 750
$process.Refresh()
if ($process.HasExited) {
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
    throw "Flask terminó durante el arranque con código $($process.ExitCode). Revise stdout: $stdoutPath y stderr: $stderrPath"
}

Write-Output "Flask iniciado de forma controlada."
Write-Output "PID: $($process.Id)"
Write-Output "stdout: $stdoutPath"
Write-Output "stderr: $stderrPath"
Write-Output "comando: $commandDisplay"
Write-Output "directorio de trabajo: $repoRoot"
Write-Output "target: $targetValue"
Write-Output "EDITOR_OFFSET_V2_ENABLED (solo proceso hijo): $v2Enabled"
Write-Output "EDITOR_OFFSET_V2_DEV_TOOLS_ENABLED (solo proceso hijo): $v2DevToolsEnabled"

