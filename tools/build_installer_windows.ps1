param(
  [Parameter(Mandatory = $true)]
  [string]$Version
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Root
$DistDir = Join-Path $Root "dist"
$OutDir = Join-Path $Root "dist_installer\\windows"

if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
New-Item -ItemType Directory -Path $OutDir | Out-Null

python -m pip install --upgrade pip pyinstaller
python setup.py build_ext --inplace
Set-Content -Path (Join-Path $Root "FireStorm\\ver") -Value $Version

$dataArgs = @(
  "--add-data", "FireStorm\\settings;settings",
  "--add-data", "FireStorm\\layouts;layouts",
  "--add-data", "FireStorm\\img;img",
  "--add-data", "FireStorm\\ver;ver",
  "--hidden-import", "tkinter",
  "--hidden-import", "PIL._tkinter_finder",
  "--collect-submodules", "PIL"
)

pyinstaller --noconfirm --clean --name "FireStorm" --onedir --windowed --icon "FireStorm\\img\\gui_icon.ico" @dataArgs "FireStorm\\FireStorm.py"

$nsis = Join-Path $Root "tools\\installer\\windows\\installer.nsi"
$makensis = (Get-Command makensis.exe -ErrorAction SilentlyContinue).Path
if (-not $makensis) {
  $fallback = "C:\\Program Files (x86)\\NSIS\\makensis.exe"
  if (Test-Path $fallback) {
    $makensis = $fallback
  }
}
if (-not $makensis) {
  throw "makensis.exe not found. Ensure NSIS is installed."
}
& $makensis "/DVERSION=$Version" "/DROOT=$Root" "/DOUTDIR=$OutDir" $nsis

Write-Host "OK: $OutDir"
