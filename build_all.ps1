$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

powershell -ExecutionPolicy Bypass -File .\build_onedir.ps1
powershell -ExecutionPolicy Bypass -File .\build_onefile.ps1

