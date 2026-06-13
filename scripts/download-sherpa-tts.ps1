# Download sherpa-onnx matcha-icefall-zh-baker TTS model for OmniSight
#
# Downloads:
#   - matcha-icefall-zh-baker.tar.bz2 (~73 MB) — Chinese female TTS model
#     Contains: model-steps-3.onnx, lexicon.txt, tokens.txt, dict/
#   - vocos-22khz-univ.onnx (~51 MB) — Universal vocoder (shared)
#
# Model: matcha-icefall-zh-baker (Matcha-TTS, Apache 2.0)
# Sample rate: 22050 Hz
# Voice: 1 (female, Chinese Mandarin)
# Text processing: Built-in FST + lexicon (NO runtime espeak-ng dependency)
#
# Source: https://github.com/k2-fsa/sherpa-onnx/releases

param(
    [string]$ModelDir = "backend\models\sherpa-voices"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ProjectRoot
$TargetDir = Join-Path $ProjectRoot $ModelDir
$ModelName = "matcha-icefall-zh-baker"
$ExtractDir = Join-Path $TargetDir $ModelName

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Download sherpa-onnx TTS Model" -ForegroundColor Cyan
Write-Host "  matcha-icefall-zh-baker (73 MB)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create target directories
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Write-Host "[+] Created: $TargetDir" -ForegroundColor Green
}
if (-not (Test-Path $ExtractDir)) {
    New-Item -ItemType Directory -Path $ExtractDir -Force | Out-Null
}

# Download URL
$BaseUrl = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"
$ArchiveFile = "$ModelName.tar.bz2"
$ArchiveUrl = "$BaseUrl/$ArchiveFile"
$ArchivePath = Join-Path $TargetDir $ArchiveFile

# Determine if we need 7z or tar
$useSevenZip = $false
if (Get-Command "tar" -ErrorAction SilentlyContinue) {
    Write-Host "[i] Using tar for extraction" -ForegroundColor DarkGray
} elseif (Get-Command "7z" -ErrorAction SilentlyContinue) {
    Write-Host "[i] Using 7z for extraction" -ForegroundColor DarkGray
    $useSevenZip = $true
} else {
    Write-Host "[!] Neither tar nor 7z found. Please install one of them." -ForegroundColor Red
    Write-Host "    tar: included in Windows 10 1803+ or Git for Windows" -ForegroundColor DarkGray
    Write-Host "    7z:  https://www.7-zip.org/" -ForegroundColor DarkGray
    exit 1
}

# Download archive
if ((Test-Path $ExtractDir) -and (Test-Path (Join-Path $ExtractDir "model-steps-3.onnx"))) {
    Write-Host "[~] Model already extracted: $ExtractDir" -ForegroundColor Yellow
} else {
    # Download if not cached
    if (-not (Test-Path $ArchivePath)) {
        Write-Host "[↓] Downloading $ArchiveFile (73 MB)..." -ForegroundColor Blue
        try {
            Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ArchivePath -UseBasicParsing
            Write-Host "[+] Downloaded: $ArchivePath ($((Get-Item $ArchivePath).Length / 1MB) MB)" -ForegroundColor Green
        } catch {
            Write-Host "[!] Failed to download: $_" -ForegroundColor Red
            Write-Host "[!] Manual download: $ArchiveUrl" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "[~] Archive cached: $ArchivePath" -ForegroundColor DarkGray
    }

    # Extract
    Write-Host "[↓] Extracting to $ExtractDir..." -ForegroundColor Blue
    try {
        if ($useSevenZip) {
            # 7z extraction: .tar.bz2 requires two passes
            $tarPath = $ArchivePath -replace '\.bz2$', ''
            & 7z x $ArchivePath -o"$TargetDir" -y | Out-Null
            & 7z x $tarPath -o"$ExtractDir" -y | Out-Null
            Remove-Item $tarPath -Force
        } else {
            tar xf $ArchivePath -C $TargetDir
        }
        Write-Host "[+] Extracted to: $ExtractDir" -ForegroundColor Green
    } catch {
        Write-Host "[!] Extraction failed: $_" -ForegroundColor Red
        Write-Host "[!] Try extracting manually with 7-Zip or tar" -ForegroundColor Red
        exit 1
    }

    # Verify extraction
    $modelFile = Join-Path $ExtractDir "model-steps-3.onnx"
    if (Test-Path $modelFile) {
        Write-Host "[+] Verified: model-steps-3.onnx ($((Get-Item $modelFile).Length / 1MB) MB)" -ForegroundColor Green
    } else {
        Write-Host "[!] Extraction verification failed — model file not found" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Download Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---- Download shared vocoder ----
$VocoderFile = "vocos-22khz-univ.onnx"
$VocoderPath = Join-Path $TargetDir $VocoderFile
$VocoderUrl = "https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/$VocoderFile"

if (Test-Path $VocoderPath) {
    Write-Host "[~] Vocoder already exists: $VocoderPath" -ForegroundColor DarkGray
} else {
    Write-Host "[↓] Downloading vocoder: $VocoderFile (51 MB)..." -ForegroundColor Blue
    try {
        Invoke-WebRequest -Uri $VocoderUrl -OutFile $VocoderPath -UseBasicParsing
        Write-Host "[+] Downloaded vocoder to: $VocoderPath" -ForegroundColor Green
    } catch {
        Write-Host "[!] Failed to download vocoder: $_" -ForegroundColor Red
        Write-Host "[!] Manual download: $VocoderUrl" -ForegroundColor Red
        Write-Host "[!] Place it at: $TargetDir" -ForegroundColor Red
    }
}

Write-Host ""

# Print .env configuration
$ModelAbsPath = (Resolve-Path $ExtractDir).Path -replace '\\', '/'

Write-Host "Add the following to your .env file:" -ForegroundColor Yellow
Write-Host ""
Write-Host "TTS_BACKEND=sherpa" -ForegroundColor White
Write-Host "SHERPA_MODEL_DIR=$ModelAbsPath" -ForegroundColor White
Write-Host "SHERPA_SPEED=1.0" -ForegroundColor White
Write-Host "SHERPA_NUM_THREADS=4" -ForegroundColor White
Write-Host ""

Write-Host "Model info:" -ForegroundColor DarkGray
Write-Host "  Model:  matcha-icefall-zh-baker" -ForegroundColor DarkGray
Write-Host "  Voice:  Chinese female (single speaker)" -ForegroundColor DarkGray
Write-Host "  Format: 22050 Hz mono PCM16" -ForegroundColor DarkGray
Write-Host "  Engine: sherpa-onnx (FST + lexicon, no espeak-ng)" -ForegroundColor DarkGray
