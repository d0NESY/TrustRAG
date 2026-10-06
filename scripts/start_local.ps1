$ErrorActionPreference = 'Stop'
$TaskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $TaskRoot
$TaskOllama = Join-Path $TaskRoot '.runtime\ollama\bin\ollama.exe'
if (-not (Test-Path -LiteralPath $TaskOllama)) { throw 'Run python scripts/download_ollama.py --version 0.35.1 first' }
try {
    $TaskVersion = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 3
    Write-Output ('Existing local Ollama is running: {0}' -f $TaskVersion.version)
    exit 0
} catch {
    # Start only when the local endpoint is absent. Do not replace an existing service.
}
$env:OLLAMA_MODELS = Join-Path $TaskRoot '.runtime\ollama\models'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_KEEP_ALIVE = '1h'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_CONTEXT_LENGTH = '2048'
$TaskProcess = Start-Process -FilePath $TaskOllama -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $TaskRoot '.runtime\ollama\server.stdout.log') -RedirectStandardError (Join-Path $TaskRoot '.runtime\ollama\server.stderr.log')
$TaskProcess.Id | Set-Content -LiteralPath .runtime\ollama\server.pid
Write-Output ('Local Ollama started; PID={0}' -f $TaskProcess.Id)
