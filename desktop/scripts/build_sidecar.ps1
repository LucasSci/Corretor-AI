Param(
    [string]$PythonExe = 'py -3.12',
    [string]$TargetTriple = 'x86_64-pc-windows-msvc'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$distDir = Join-Path $repoRoot 'desktop\src-tauri\binaries'

Write-Host 'Gerando sidecar Python com PyInstaller (one-folder)...'
Push-Location $repoRoot
try {
    & $PythonExe -m pip install pyinstaller
    & $PythonExe -m PyInstaller --noconfirm --clean --onedir --name corretor-backend desktop\sidecar\launcher.py --paths .
    $sourceExe = Join-Path $repoRoot 'dist\corretor-backend\corretor-backend.exe'
    $targetExe = Join-Path $distDir "corretor-backend-$TargetTriple.exe"
    Copy-Item $sourceExe $targetExe -Force
    Write-Host "Sidecar copiado para $targetExe"
}
finally {
    Pop-Location
}
