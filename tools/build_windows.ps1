param([switch]$InstallDependencies)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -3.14 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment.' }
    $InstallDependencies = $true
}
$pythonPath = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if ($InstallDependencies) {
    & $pythonPath -m pip install -r requirements.lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& $pythonPath -m unittest discover -s tests -p 'test_*.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& $pythonPath -m PyInstaller --noconfirm --distpath release-v08 desktop.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
& $pythonPath tools\prepare_distribution.py
if ($LASTEXITCODE -ne 0) { throw 'Distribution preparation failed.' }
