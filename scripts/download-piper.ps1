# Download Piper TTS engine and Chinese voice model
# ==================================================
# Piper: https://github.com/rhasspy/piper
# Voices: https://huggingface.co/rhasspy/piper-voices
#
# Usage:
#   .\scripts\download-piper.ps1
#
# This downloads:
#   1. piper.exe + DLLs → backend/bin/piper/
#   2. zh_CN-huayan-medium voice → backend/models/piper-voices/
#   3. en_US-lessac-medium voice → backend/models/piper-voices/ (fallback)
#

param(
    [string]$PiperVersion = "2023.11.14-2",
    [string]$OutputDir = "backend"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Faster downloads

$binDir = Join-Path $OutputDir "bin\piper"
$modelDir = Join-Path $OutputDir "models\piper-voices"

Write-Host "=== OmniSight Piper TTS Download ===" -ForegroundColor Cyan
Write-Host ""

# ---- Create directories ----
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

# ---- 1. Piper executable ----
Write-Host "[1/2] Downloading Piper $PiperVersion (Windows)..." -ForegroundColor Yellow

$piperUrl = "https://github.com/rhasspy/piper/releases/download/$PiperVersion/piper_windows_amd64.zip"
$piperZip = Join-Path $env:TEMP "piper_windows_amd64.zip"

try {
    Invoke-WebRequest -Uri $piperUrl -OutFile $piperZip -UseBasicParsing
    Write-Host "  Downloaded: $([math]::Round((Get-Item $piperZip).Length / 1MB, 1)) MB"
} catch {
    Write-Host "  ERROR: Failed to download Piper." -ForegroundColor Red
    Write-Host "  Check https://github.com/rhasspy/piper/releases for the latest version."
    Write-Host "  Try: .\scripts\download-piper.ps1 -PiperVersion '2024.x.y'"
    exit 1
}

Write-Host "  Extracting to $binDir..."
Expand-Archive -Path $piperZip -DestinationPath $binDir -Force
Remove-Item $piperZip

$piperExe = Join-Path $binDir "piper\piper.exe"
if (Test-Path $piperExe) {
    Write-Host "  piper.exe ready: $piperExe" -ForegroundColor Green
} else {
    # Files might be at root of zip, not in subdirectory
    $piperExe = Join-Path $binDir "piper.exe"
    if (Test-Path $piperExe) {
        Write-Host "  piper.exe ready: $piperExe" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: piper.exe not found in extracted files." -ForegroundColor Red
        Write-Host "  Contents of $binDir :"
        Get-ChildItem $binDir -Recurse | ForEach-Object { Write-Host "    $_" }
    }
}

# ---- 2. Voice models ----
Write-Host ""
Write-Host "[2/2] Downloading voice models..." -ForegroundColor Yellow

$voiceBaseUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

$voices = @(
    @{
        Name = "zh_CN-huayan-medium"
        Path = "zh/zh_CN/huayan/medium/zh_CN-huayan-medium"
        Desc = "Chinese (Mandarin) female voice"
    },
    @{
        Name = "en_US-lessac-medium"
        Path = "en/en_US/lessac/medium/en_US-lessac-medium"
        Desc = "American English female voice"
    }
)

# HuggingFace requires a browser-like User-Agent for direct downloads
$headers = @{
    "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

foreach ($voice in $voices) {
    Write-Host "  Downloading $($voice.Name) — $($voice.Desc)..."

    $modelFile = Join-Path $modelDir "$($voice.Name).onnx"
    $configFile = Join-Path $modelDir "$($voice.Name).onnx.json"

    $modelUrl = "$voiceBaseUrl/$($voice.Path).onnx"
    $configUrl = "$voiceBaseUrl/$($voice.Path).onnx.json"

    try {
        if (Test-Path $modelFile) {
            Write-Host "    Model already exists, skipping: $modelFile"
        } else {
            Invoke-WebRequest -Uri $modelUrl -OutFile $modelFile -Headers $headers -UseBasicParsing
            $sizeMB = [math]::Round((Get-Item $modelFile).Length / 1MB, 1)
            Write-Host "    Model: $sizeMB MB" -ForegroundColor Green
        }
    } catch {
        Write-Host "    WARNING: Failed to download $($voice.Name) model." -ForegroundColor DarkYellow
    }

    try {
        if (Test-Path $configFile) {
            Write-Host "    Config already exists, skipping: $configFile"
        } else {
            Invoke-WebRequest -Uri $configUrl -OutFile $configFile -Headers $headers -UseBasicParsing
            Write-Host "    Config: OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "    WARNING: Failed to download $($voice.Name) config." -ForegroundColor DarkYellow
    }
}

# ---- Done ----
Write-Host ""
Write-Host "=== Download Complete ===" -ForegroundColor Cyan
Write-Host ""

$zhModel = Join-Path $modelDir "zh_CN-huayan-medium.onnx"
if (Test-Path $zhModel) {
    Write-Host "To use Piper TTS, add these to backend/.env:" -ForegroundColor White
    Write-Host ""
    Write-Host "  TTS_BACKEND=piper" -ForegroundColor Gray
    Write-Host "  PIPER_EXECUTABLE=$(Resolve-Path $piperExe)" -ForegroundColor Gray
    Write-Host "  PIPER_MODEL=$(Resolve-Path $zhModel)" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "Voice model download may have failed. Check the URLs manually:" -ForegroundColor DarkYellow
    Write-Host "  $voiceBaseUrl"
}
