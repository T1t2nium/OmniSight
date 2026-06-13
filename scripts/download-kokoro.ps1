# Download Kokoro 82M ONNX TTS model files for OmniSight
#
# Downloads:
#   - kokoro-v1.0.int8.onnx (86 MB) — quantized ONNX model (recommended for CPU)
#   - voices-v1.0.bin       (28 MB) — voice embeddings for 40+ voices
#
# Model license: Apache 2.0 (commercial use allowed)
# Source: https://github.com/thewh1teagle/kokoro-onnx/releases
#
# Alternative: For even better Chinese quality, use the v1.1-zh model:
#   - kokoro-v1.1-zh.onnx — Chinese-focused model with 100+ speaker variants
#   Available from: https://huggingface.co/hexgrad/Kokoro-82M

param(
    [string]$ModelDir = "backend\models\kokoro-voices",
    [string]$Variant = "v1.0"  # "v1.0" or "v1.1-zh"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ProjectRoot
$TargetDir = Join-Path $ProjectRoot $ModelDir

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Download Kokoro 82M ONNX TTS Model" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create target directory
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Write-Host "[+] Created: $TargetDir" -ForegroundColor Green
}

# Download URLs
$BaseUrl = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
$ModelFile = "kokoro-v1.0.int8.onnx"
$VoicesFile = "voices-v1.0.bin"

$ModelUrl = "$BaseUrl/$ModelFile"
$VoicesUrl = "$BaseUrl/$VoicesFile"

$ModelPath = Join-Path $TargetDir $ModelFile
$VoicesPath = Join-Path $TargetDir $VoicesFile

# Download model
if (Test-Path $ModelPath) {
    Write-Host "[~] Model already exists: $ModelPath ($((Get-Item $ModelPath).Length / 1MB) MB)" -ForegroundColor Yellow
} else {
    Write-Host "[↓] Downloading model: $ModelFile (86 MB)..." -ForegroundColor Blue
    try {
        Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelPath -UseBasicParsing
        Write-Host "[+] Downloaded: $ModelPath ($((Get-Item $ModelPath).Length / 1MB) MB)" -ForegroundColor Green
    } catch {
        Write-Host "[!] Failed to download model: $_" -ForegroundColor Red
        Write-Host "[!] You can download manually from: $ModelUrl" -ForegroundColor Red
        exit 1
    }
}

# Download voices
if (Test-Path $VoicesPath) {
    Write-Host "[~] Voices already exist: $VoicesPath ($((Get-Item $VoicesPath).Length / 1MB) MB)" -ForegroundColor Yellow
} else {
    Write-Host "[↓] Downloading voices: $VoicesFile (28 MB)..." -ForegroundColor Blue
    try {
        Invoke-WebRequest -Uri $VoicesUrl -OutFile $VoicesPath -UseBasicParsing
        Write-Host "[+] Downloaded: $VoicesPath ($((Get-Item $VoicesPath).Length / 1MB) MB)" -ForegroundColor Green
    } catch {
        Write-Host "[!] Failed to download voices: $_" -ForegroundColor Red
        Write-Host "[!] You can download manually from: $VoicesUrl" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Download Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Print .env configuration
$ModelAbsPath = (Resolve-Path $ModelPath).Path -replace '\\', '/'
$VoicesAbsPath = (Resolve-Path $VoicesPath).Path -replace '\\', '/'

Write-Host "Add the following to your .env file:" -ForegroundColor Yellow
Write-Host ""
Write-Host "TTS_BACKEND=kokoro" -ForegroundColor White
Write-Host "KOKORO_MODEL_PATH=$ModelAbsPath" -ForegroundColor White
Write-Host "KOKORO_VOICES_PATH=$VoicesAbsPath" -ForegroundColor White
Write-Host "KOKORO_VOICE=zf_xiaobei" -ForegroundColor White
Write-Host "KOKORO_SPEED=1.0" -ForegroundColor White
Write-Host "KOKORO_LANG=zh" -ForegroundColor White
Write-Host ""

Write-Host "Available Chinese voices (after model download):" -ForegroundColor DarkGray
Write-Host "  Female: zf_xiaobei, zf_xiaoni, zf_xiaoxiao, zf_xiaoyi" -ForegroundColor DarkGray
Write-Host "  Male:   zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang" -ForegroundColor DarkGray
