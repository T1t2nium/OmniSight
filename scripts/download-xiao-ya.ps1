$modelDir = "E:\OmniSight\backend\models\piper-voices"
$headers = @{ "User-Agent" = "Mozilla/5.0" }

Write-Host "Downloading xiao_ya voice model..." -ForegroundColor Yellow

Invoke-WebRequest `
    -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/xiao_ya/medium/zh_CN-xiao_ya-medium.onnx" `
    -OutFile "$modelDir\zh_CN-xiao_ya-medium.onnx" `
    -Headers $headers

$sizeMB = [math]::Round((Get-Item "$modelDir\zh_CN-xiao_ya-medium.onnx").Length / 1MB, 1)
Write-Host "Model: $sizeMB MB" -ForegroundColor Green

Invoke-WebRequest `
    -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/xiao_ya/medium/zh_CN-xiao_ya-medium.onnx.json" `
    -OutFile "$modelDir\zh_CN-xiao_ya-medium.onnx.json" `
    -Headers $headers

Write-Host "Config: OK" -ForegroundColor Green
Write-Host "Done! Now update backend/.env:" -ForegroundColor Cyan
Write-Host "  PIPER_MODEL=E:\OmniSight\backend\models\piper-voices\zh_CN-xiao_ya-medium.onnx"
