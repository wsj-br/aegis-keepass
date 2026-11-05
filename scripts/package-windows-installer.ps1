# Wrap dist/aegis-keepass.exe in an Inno Setup installer.
# Edge WebView2 stays on the host; it is not inside the installer.
# Run from the repo root after PyInstaller, on Windows.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$Binary = Join-Path $Root 'dist\aegis-keepass.exe'
$Icon = Join-Path $Root 'build\aegis-keepass.ico'
$Iss = Join-Path $Root 'packaging\aegis-keepass.iss'
if (-not (Test-Path -LiteralPath $Binary)) {
    Fail "Missing $Binary. Run PyInstaller first."
}
if (-not (Test-Path -LiteralPath $Icon)) {
    Fail "Missing $Icon. The Windows PyInstaller build should have written it."
}
if (-not (Test-Path -LiteralPath $Iss)) {
    Fail "Missing $Iss."
}

$Arch = $env:PROCESSOR_ARCHITECTURE
if (-not $Arch -or $Arch -eq 'x86') {
    $Arch = $env:PROCESSOR_ARCHITEW6432
}
switch ($Arch) {
    'AMD64' {
        $ArchLabel = 'x64'
        $AllowedArch = 'x64os'
    }
    'ARM64' {
        $ArchLabel = 'arm64'
        $AllowedArch = 'arm64'
    }
    default {
        Fail "Unsupported Windows architecture: $Arch"
    }
}

$VersionPy = Get-Content -LiteralPath (Join-Path $Root 'app\_version.py') -Raw
if ($VersionPy -notmatch '__version__\s*=\s*"([^"]+)"') {
    Fail 'Could not read __version__ from app/_version.py.'
}
$Version = $Matches[1]

# 64-bit compiler so the Windows ARM runner can run it (x64 emulation).
# The 32-bit Inno Setup 6 installer does not run on Windows 11 ARM.
$InnoVersion = '7.1.1'
$InnoSha256 = '8a5a6711c3766a6e5fb74f280ba0e3551e719ce94538d901fdbd1f8f9920b3f0'
$ToolDir = Join-Path $Root 'build\innosetup'
$Installer = Join-Path $ToolDir "innosetup-$InnoVersion.exe"
$Iscc = Join-Path $ToolDir 'ISCC.exe'
New-Item -ItemType Directory -Force -Path $ToolDir | Out-Null

if (-not (Test-Path -LiteralPath $Iscc)) {
    Write-Host "Downloading Inno Setup $InnoVersion ..."
    $Partial = "$Installer.partial"
    Invoke-WebRequest -Uri "https://github.com/jrsoftware/issrc/releases/download/is-7_1_1/innosetup-$InnoVersion-x64.exe" -OutFile $Partial
    $Hash = (Get-FileHash -LiteralPath $Partial -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Hash -ne $InnoSha256) {
        Fail "Inno Setup checksum mismatch: $Hash"
    }
    Move-Item -LiteralPath $Partial -Destination $Installer -Force
    $Args = @(
        '/VERYSILENT',
        '/SUPPRESSMSGBOXES',
        '/NORESTART',
        '/SP-',
        "/DIR=$ToolDir"
    )
    $Proc = Start-Process -FilePath $Installer -ArgumentList $Args -Wait -PassThru
    if ($Proc.ExitCode -ne 0) {
        Fail "Inno Setup installer exited $($Proc.ExitCode)."
    }
}
if (-not (Test-Path -LiteralPath $Iscc)) {
    Fail "ISCC.exe not found at $Iscc."
}

$Output = Join-Path $Root "dist\aegis-keepass-$Version-windows-$ArchLabel.exe"
if (Test-Path -LiteralPath $Output) {
    Remove-Item -LiteralPath $Output -Force
}

Write-Host "Building $Output ..."
& $Iscc "/DAppVersion=$Version" "/DArchLabel=$ArchLabel" "/DAllowedArch=$AllowedArch" $Iss
if ($LASTEXITCODE -ne 0) {
    Fail "ISCC exited $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $Output)) {
    Fail "Installer was not written to $Output."
}

Write-Host ""
Write-Host "Installer: $Output"
