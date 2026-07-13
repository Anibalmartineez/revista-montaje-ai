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

function Test-SamePath {
    param([string]$Left, [string]$Right)
    if ([string]::IsNullOrWhiteSpace($Left) -or [string]::IsNullOrWhiteSpace($Right)) {
        return $false
    }
    $leftFull = [System.IO.Path]::GetFullPath($Left).TrimEnd('\')
    $rightFull = [System.IO.Path]::GetFullPath($Right).TrimEnd('\')
    return [string]::Equals($leftFull, $rightFull, [System.StringComparison]::OrdinalIgnoreCase)
}

$repoRoot = Get-RepositoryRoot
Set-Location -LiteralPath $repoRoot

$runtimeDir = Join-Path $repoRoot ".codex-runtime\editor-offset-local-qa"
$pidPath = Join-Path $runtimeDir "flask.pid"
$metadataPath = Join-Path $runtimeDir "process.json"
$expectedPythonPath = Join-Path $repoRoot "venv\Scripts\python.exe"
$expectedEntryPoint = Join-Path $repoRoot "app.py"

if (-not (Test-Path -LiteralPath $pidPath -PathType Leaf)) {
    Write-Output "No existe un PID guardado por la Skill. No se detuvo ningún proceso."
    exit 0
}

$pidText = (Get-Content -LiteralPath $pidPath -Raw).Trim()
$savedPid = 0
if (-not [int]::TryParse($pidText, [ref]$savedPid) -or $savedPid -le 0) {
    Write-Output "El archivo PID no contiene un PID numérico válido. No se detuvo ningún proceso: $pidPath"
    exit 0
}

$process = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
if ($null -eq $process) {
    Remove-Item -LiteralPath $pidPath -Force
    Write-Output "El PID $savedPid ya no existe. Se eliminó únicamente el archivo PID obsoleto."
    exit 0
}

if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
    throw "El proceso existe, pero faltan los metadatos de la Skill. No se detuvo el PID $savedPid."
}

try {
    $metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
} catch {
    throw "Los metadatos no son JSON válido. No se detuvo el PID $savedPid. Detalle: $($_.Exception.Message)"
}

$verificationErrors = [System.Collections.Generic.List[string]]::new()
if ([int]$metadata.pid -ne $savedPid) {
    $verificationErrors.Add("el PID de metadatos no coincide")
}
if (-not (Test-SamePath -Left ([string]$metadata.executable_path) -Right $expectedPythonPath)) {
    $verificationErrors.Add("la ruta del intérprete registrada no coincide con el venv")
}
if (-not (Test-SamePath -Left ([string]$metadata.entry_point) -Right $expectedEntryPoint)) {
    $verificationErrors.Add("el archivo de entrada registrado no coincide con app.py")
}
if (-not (Test-SamePath -Left ([string]$metadata.working_directory) -Right $repoRoot)) {
    $verificationErrors.Add("el directorio de trabajo registrado no coincide con la raíz Git")
}
if ([string]$metadata.marker -ne "editor-offset-local-qa") {
    $verificationErrors.Add("falta el marcador esperado de la Skill")
}

try {
    $actualProcessPath = $process.Path
} catch {
    $actualProcessPath = $null
}
if ($process.ProcessName -ine "python") {
    $verificationErrors.Add("el nombre del proceso activo no es python")
}
if (-not (Test-SamePath -Left $actualProcessPath -Right $expectedPythonPath)) {
    $verificationErrors.Add("la ruta del ejecutable activo no coincide con el Python del venv")
}

try {
    $recordedStart = [DateTime]::Parse(
        [string]$metadata.process_start_time_utc,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::RoundtripKind
    ).ToUniversalTime()
    $actualStart = $process.StartTime.ToUniversalTime()
    if ([Math]::Abs(($actualStart - $recordedStart).TotalSeconds) -gt 3) {
        $verificationErrors.Add("la hora de inicio no coincide")
    }
} catch {
    $verificationErrors.Add("no se pudo verificar la hora de inicio")
}

try {
    $cimProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $savedPid" -ErrorAction Stop
    if ($null -eq $cimProcess) {
        $verificationErrors.Add("no se obtuvo información Win32 del proceso")
    } else {
        if (-not (Test-SamePath -Left ([string]$cimProcess.ExecutablePath) -Right $expectedPythonPath)) {
            $verificationErrors.Add("Win32 reporta un ejecutable diferente")
        }
        $commandLine = [string]$cimProcess.CommandLine
        if ($commandLine -notmatch "editor-offset-local-qa" -or $commandLine -notmatch "from app import app") {
            $verificationErrors.Add("la línea de comandos no contiene el marcador y punto de entrada esperados")
        }
    }
} catch {
    $verificationErrors.Add("no se pudo verificar la línea de comandos mediante Win32_Process")
}

if ($verificationErrors.Count -gt 0) {
    throw "No hay verificación suficiente para detener el PID $savedPid. No se realizó ninguna detención. Motivos: $($verificationErrors -join '; ')"
}

Write-Output "Verificación satisfactoria: PID, ejecutable, ruta del venv, app.py, raíz, hora de inicio y línea de comandos coinciden."
Stop-Process -Id $savedPid -ErrorAction Stop
$deadline = (Get-Date).AddSeconds(5)
do {
    $remainingProcess = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
    if ($null -eq $remainingProcess) {
        break
    }
    Start-Sleep -Milliseconds 200
} while ((Get-Date) -lt $deadline)

if ($null -ne (Get-Process -Id $savedPid -ErrorAction SilentlyContinue)) {
    Write-Warning "El PID $savedPid no terminó en 5 segundos. No se aplicó una detención forzada y se conservó el archivo PID."
    exit 1
}

Remove-Item -LiteralPath $pidPath -Force
Write-Output "PID detenido: $savedPid"
Write-Output "Se eliminó el archivo PID: $pidPath"
Write-Output "Se conservaron los metadatos y logs del directorio: $runtimeDir"
if ($metadata.stdout_path) { Write-Output "stdout conservado: $($metadata.stdout_path)" }
if ($metadata.stderr_path) { Write-Output "stderr conservado: $($metadata.stderr_path)" }
