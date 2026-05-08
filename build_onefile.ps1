$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

python -m pip install -r requirements.txt -r requirements-dev.txt

$releasePath = Join-Path $PSScriptRoot "release"
$workPath = Join-Path $PSScriptRoot "build\onefile"
$specPath = Join-Path $PSScriptRoot "build\specs_onefile"

if (Test-Path $releasePath) {
  try { Remove-Item -Recurse -Force $releasePath } catch { throw "Failed to clean release. Close any running app or open Explorer windows that lock files." }
}
if (Test-Path $workPath) {
  try { Remove-Item -Recurse -Force $workPath } catch { throw "Failed to clean build/onefile. Close any windows that lock files." }
}
if (Test-Path $specPath) {
  try { Remove-Item -Recurse -Force $specPath } catch { }
}

python -m PyInstaller --noconsole --onefile --clean --noconfirm --name InvoiceMerger --distpath release --workpath $workPath --specpath $specPath app.py

Write-Host "OK: release/InvoiceMerger.exe"

