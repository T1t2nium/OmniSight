# Download sherpa-onnx TTS model for OmniSight
#
# Default model: vits-melo-tts-zh_en (163 MB, 44100 Hz, bilingual Chinese+English)
# Alternative: matcha-icefall-zh-baker (73 MB, 22050 Hz, Chinese only, needs vocoder)
#
# All models: Apache 2.0 license, built-in Chinese FST+lexicon text processing
# Source: https://github.com/k2-fsa/sherpa-onnx/releases

param(
    [string]$ModelDir = "backend\models\sherpa-voices",
    [ValidateSet("vits-melo", "matcha", "all")]
    [string]$Model = "vits-melo"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ProjectRoot
$TargetDir = Join-Path $ProjectRoot $ModelDir

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Download sherpa-onnx TTS Model" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create target directory
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Write-Host "[+] Created: $TargetDir" -ForegroundColor Green
}

$BaseUrl = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"

function Download-And-Extract($ArchiveName, $DisplayName) {
    $ArchiveFile = "$ArchiveName.tar.bz2"
    $ArchiveUrl = "$BaseUrl/$ArchiveFile"
    $ArchivePath = Join-Path $TargetDir $ArchiveFile
    $ExtractDir = Join-Path $TargetDir $ArchiveName

    if ((Test-Path $ExtractDir) -and (Test-Path (Join-Path $ExtractDir "model.onnx"))) {
        Write-Host "[~] $DisplayName already extracted: $ExtractDir" -ForegroundColor Yellow
        return $ExtractDir
    }

    if (-not (Test-Path $ArchivePath)) {
        Write-Host "[↓] Downloading $DisplayName..." -ForegroundColor Blue
        try {
            Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ArchivePath -UseBasicParsing
            Write-Host "[+] Downloaded: $((Get-Item $ArchivePath).Length / 1MB) MB" -ForegroundColor Green
        } catch {
            Write-Host "[!] Download failed: $_" -ForegroundColor Red
            Write-Host "[!] Manual: $ArchiveUrl" -ForegroundColor Red
            throw
        }
    } else {
        Write-Host "[~] Archive cached: $ArchivePath" -ForegroundColor DarkGray
    }

    Write-Host "[↓] Extracting to $ExtractDir..." -ForegroundColor Blue
    try {
        if (Get-Command "tar" -ErrorAction SilentlyContinue) {
            tar xf $ArchivePath -C $TargetDir
        } elseif (Get-Command "7z" -ErrorAction SilentlyContinue) {
            $tarPath = $ArchivePath -replace '\.bz2$', ''
            & 7z x $ArchivePath -o"$TargetDir" -y | Out-Null
            & 7z x $tarPath -o"$ExtractDir" -y | Out-Null
            Remove-Item $tarPath -Force
        } else {
            Write-Host "[!] Neither tar nor 7z found. Install Git for Windows or 7-Zip." -ForegroundColor Red
            throw
        }
        Write-Host "[+] Extracted: $ExtractDir" -ForegroundColor Green
    } catch {
        Write-Host "[!] Extraction failed: $_" -ForegroundColor Red
        throw
    }

    return $ExtractDir
}

$ExtractedDir = ""

# ---- VITS-Melo (default, recommended) ----
if ($Model -eq "vits-melo" -or $Model -eq "all") {
    $ExtractedDir = Download-And-Extract "vits-melo-tts-zh_en" "VITS-Melo (bilingual CN+EN, 163 MB)"
}

# ---- Matcha (alternative) ----
if ($Model -eq "matcha" -or $Model -eq "all") {
    $ExtractedDir = Download-And-Extract "matcha-icefall-zh-baker" "Matcha-TTS (Chinese only, 73 MB)"

    # Matcha needs separate vocoder
    $VocoderFile = "vocos-22khz-univ.onnx"
    $VocoderPath = Join-Path $TargetDir $VocoderFile
    $VocoderUrl = "https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/$VocoderFile"
    if (-not (Test-Path $VocoderPath)) {
        Write-Host "[↓] Downloading vocoder ($VocoderFile, 51 MB)..." -ForegroundColor Blue
        Invoke-WebRequest -Uri $VocoderUrl -OutFile $VocoderPath -UseBasicParsing
        Write-Host "[+] Vocoder downloaded" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Download Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Print .env configuration
if ($ExtractedDir) {
    $ModelAbsPath = (Resolve-Path $ExtractedDir).Path -replace '\\', '/'
    Write-Host "Add to your .env:" -ForegroundColor Yellow
    Write-Host "  TTS_BACKEND=sherpa" -ForegroundColor White
    Write-Host "  SHERPA_MODEL_DIR=$ModelAbsPath" -ForegroundColor White
    Write-Host "  SHERPA_SPEED=1.0" -ForegroundColor White
    Write-Host "  SHERPA_NUM_THREADS=4" -ForegroundColor White
    Write-Host ""
}

Write-Host "Model info:" -ForegroundColor DarkGray
Write-Host "  vits-melo-tts-zh_en: 44100 Hz, bilingual CN+EN, 163 MB" -ForegroundColor DarkGray
Write-Host "  matcha-icefall-zh-baker: 22050 Hz, Chinese only, 73 MB + vocoder" -ForegroundColor DarkGray
Write-Host "  Engine: sherpa-onnx (built-in FST + lexicon, NO espeak-ng)" -ForegroundColor DarkGray
Write-Host "  Auto-fix: ORT DLL replaced if system onnxruntime >= 1.20 is installed" -ForegroundColor DarkGray
