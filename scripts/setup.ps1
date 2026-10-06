param([string]$TaskPython = 'python')
$ErrorActionPreference = 'Stop'
$TaskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $TaskRoot
& $TaskPython -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 is required'"
if ($LASTEXITCODE -ne 0) { throw 'Python version check failed' }
$TaskPoetryPython = Join-Path $TaskRoot '.tools\poetry\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $TaskPoetryPython)) {
    & $TaskPython -m venv .tools\poetry
    if ($LASTEXITCODE -ne 0) { throw 'Poetry tool environment creation failed' }
}
& $TaskPoetryPython -m pip install --index-url https://pypi.org/simple --disable-pip-version-check poetry==1.8.5
if ($LASTEXITCODE -ne 0) { throw 'Poetry installation failed' }
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & $TaskPython -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Project environment creation failed' }
}
$env:VIRTUAL_ENV = (Resolve-Path -LiteralPath .venv).Path
$env:POETRY_CACHE_DIR = Join-Path $TaskRoot '.runtime\poetry-cache'
$env:POETRY_KEYRING_ENABLED = 'false'
& $TaskPoetryPython -m poetry install --only main,dev --no-interaction
if ($LASTEXITCODE -ne 0) { throw 'Project dependency installation failed' }
Write-Output 'Installed the locked project environment; Poetry remains isolated in .tools.'
