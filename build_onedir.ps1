$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

python -m pip install -r requirements.txt -r requirements-dev.txt

$distPath = Join-Path $PSScriptRoot "dist"
$workPath = Join-Path $PSScriptRoot "build\onedir"
$specPath = Join-Path $PSScriptRoot "build\specs"

if (Test-Path $distPath) {
  try { Remove-Item -Recurse -Force $distPath } catch { throw "Failed to clean dist. Close any running app or open Explorer windows that lock files." }
}
if (Test-Path $workPath) {
  try { Remove-Item -Recurse -Force $workPath } catch { throw "Failed to clean build/onedir. Close any windows that lock files." }
}
if (Test-Path $specPath) {
  try { Remove-Item -Recurse -Force $specPath } catch { }
}

python -m PyInstaller --noconsole --onedir --clean --noconfirm --name InvoiceMerger --distpath dist --workpath $workPath --specpath $specPath app.py

Write-Host "OK: dist/InvoiceMerger/InvoiceMerger.exe"

