# Start Aegis-KeePass OTP Sync via WSL Containers (wslc.exe) on Windows.
# Requires the WSL Containers public preview (no Docker Desktop).
# Docs: https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers
#
# Prerequisites (once):
#   wsl --update --pre-release
#   wsl --shutdown
#   wslc --version
#
# One-liner (PowerShell, defaults):
#   irm https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start-wslc.ps1 | iex
#
# One-liner with arguments:
#   & ([scriptblock]::Create((irm https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start-wslc.ps1))) -Detach
#
# Download and run:
#   irm https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start-wslc.ps1 -OutFile aegis-keepass-start-wslc.ps1
#   .\aegis-keepass-start-wslc.ps1 -Detach
#   .\aegis-keepass-start-wslc.ps1 -Port 9090 -Tag 0.1.1 -Open
#   .\aegis-keepass-start-wslc.ps1 -Stop
#
# Environment overrides (optional with irm | iex):
#   $env:IMAGE_TAG = "0.1.1"; $env:PORT = "9090"; irm ... | iex

[CmdletBinding()]
param(
    [string]$Tag = $(if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }),
    [int]$Port = $(
        if ($env:PORT) { [int]$env:PORT }
        elseif ($env:HOST_PORT) { [int]$env:HOST_PORT }
        else { 8580 }
    ),
    [string]$Name = $(if ($env:CONTAINER_NAME) { $env:CONTAINER_NAME } else { "aegis-keepass" }),
    [string]$ImageRepo = $(if ($env:IMAGE_REPO) { $env:IMAGE_REPO } else { "ghcr.io/wsj-br/aegis-keepass" }),
    [switch]$Detach,
    [switch]$NoPull,
    [switch]$Open,
    [switch]$Stop,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Show-Usage {
    @"
Usage: aegis-keepass-start-wslc.ps1 [-Tag TAG] [-Port PORT] [-Name NAME] [-Detach] [-NoPull] [-Open] [-Stop]

Pull and run Aegis-KeePass OTP Sync with Microsoft WSL Containers (wslc).
Port publishing is localhost-only (WSL Containers default).

Parameters:
  -Tag TAG       Image tag (default: latest, or `$env:IMAGE_TAG)
  -Port PORT     Host port (default: 8580, or `$env:PORT / `$env:HOST_PORT)
  -Name NAME     Container name (default: aegis-keepass)
  -Detach        Run in the background
  -NoPull        Skip image pull (use local image if present)
  -Open          Open http://127.0.0.1:<port> in the default browser when ready
  -Stop          Stop the named container, then exit
  -Help          Show this help

Prerequisites:
  wsl --update --pre-release
  wsl --shutdown
  wslc --version

Environment:
  IMAGE_REPO, IMAGE_TAG, CONTAINER_NAME, PORT / HOST_PORT
  SESSION_TIMEOUT_SECONDS, MAX_IN_MEMORY_UPLOAD_BYTES, MAX_UPLOAD_BYTES
  FLASK_SECRET_KEY (optional)

Examples:
  irm https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start-wslc.ps1 | iex
  .\aegis-keepass-start-wslc.ps1 -Detach -Port 9090
  .\aegis-keepass-start-wslc.ps1 -Tag 0.1.1 -Open
  .\aegis-keepass-start-wslc.ps1 -Stop

Equivalent manual commands:
  wslc pull ghcr.io/wsj-br/aegis-keepass:latest
  wslc run --rm -d -p 8580:8580 --name aegis-keepass --tmpfs /tmp:size=64M,mode=1777 ghcr.io/wsj-br/aegis-keepass:latest
  wslc container stop aegis-keepass
"@
}

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

function Resolve-WslcCommand {
    if (Get-Command wslc -ErrorAction SilentlyContinue) {
        return "wslc"
    }
    # Official alias that runs wslc.exe
    if (Get-Command container -ErrorAction SilentlyContinue) {
        return "container"
    }
    return $null
}

function Test-WslcReady {
    $cmd = Resolve-WslcCommand
    if (-not $cmd) {
        Fail @"
Missing required command: wslc (WSL Containers).
Install/update the preview, then retry:
  wsl --update --pre-release
  wsl --shutdown
  wslc --version
Docs: https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers
"@
    }

    try {
        & $cmd --version 1>$null 2>$null
        if ($LASTEXITCODE -ne 0) {
            Fail "wslc is present but not working. Try: wsl --update --pre-release && wsl --shutdown"
        }
    }
    catch {
        Fail "wslc is present but not working. Try: wsl --update --pre-release && wsl --shutdown"
    }

    return $cmd
}

function Test-ContainerListed([string]$Wslc, [string]$ContainerName) {
    $output = & $Wslc container list --all 2>$null | Out-String
    if (-not $output) {
        return $false
    }
    # Match whole word in list output (names / IDs appear as tokens).
    return [bool]($output -match "(?m)(?:^|\s)$([regex]::Escape($ContainerName))(?:\s|$)")
}

function Stop-AegisWslcContainer([string]$Wslc, [string]$ContainerName) {
    if (Test-ContainerListed -Wslc $Wslc -ContainerName $ContainerName) {
        Write-Host "Stopping container '${ContainerName}'..."
        & $Wslc container stop $ContainerName 1>$null 2>$null | Out-Null
        # --rm containers are removed on stop; otherwise remove explicitly.
        & $Wslc container rm $ContainerName 1>$null 2>$null | Out-Null
        Write-Host "Stopped '${ContainerName}'."
    }
    else {
        Write-Host "No container named '${ContainerName}' found."
    }
}

if ($Help) {
    Show-Usage
    exit 0
}

# When piped via `irm | iex`, param() may not receive CLI args; allow env fallbacks.
if ($env:AEGIS_DETACH -eq "1") { $Detach = $true }
if ($env:AEGIS_NO_PULL -eq "1") { $NoPull = $true }
if ($env:AEGIS_OPEN -eq "1") { $Open = $true }
if ($env:AEGIS_STOP -eq "1") { $Stop = $true }

if ($Port -lt 1 -or $Port -gt 65535) {
    Fail "Port out of range: $Port"
}

$Wslc = Test-WslcReady

$Image = "${ImageRepo}:${Tag}"
$Url = "http://127.0.0.1:${Port}"

$sessionTimeout = if ($env:SESSION_TIMEOUT_SECONDS) { $env:SESSION_TIMEOUT_SECONDS } else { "1800" }
$maxInMemory = if ($env:MAX_IN_MEMORY_UPLOAD_BYTES) { $env:MAX_IN_MEMORY_UPLOAD_BYTES } else { "33554432" }
$maxUpload = if ($env:MAX_UPLOAD_BYTES) { $env:MAX_UPLOAD_BYTES } else { "52428800" }

if ($Stop) {
    Stop-AegisWslcContainer -Wslc $Wslc -ContainerName $Name
    exit 0
}

if (Test-ContainerListed -Wslc $Wslc -ContainerName $Name) {
    Write-Host "Removing existing container '${Name}'..."
    & $Wslc container stop $Name 1>$null 2>$null | Out-Null
    & $Wslc container rm $Name 1>$null 2>$null | Out-Null
}

if (-not $NoPull) {
    Write-Host "Pulling ${Image}..."
    & $Wslc pull $Image
    if ($LASTEXITCODE -ne 0) {
        # Fallback for builds that only expose the image subgroup.
        & $Wslc image pull $Image
        if ($LASTEXITCODE -ne 0) {
            Fail "wslc pull failed for ${Image}"
        }
    }
}

# WSL Containers publish ports to localhost only. --tmpfs is supported; --read-only
# is not always available on the preview CLI, so it is omitted here.
$runArgs = @(
    "run",
    "--name", $Name,
    "--rm",
    "-p", "${Port}:8580",
    "--tmpfs", "/tmp:size=64M,mode=1777",
    "-e", "SESSION_TIMEOUT_SECONDS=${sessionTimeout}",
    "-e", "MAX_IN_MEMORY_UPLOAD_BYTES=${maxInMemory}",
    "-e", "MAX_UPLOAD_BYTES=${maxUpload}"
)

if ($env:FLASK_SECRET_KEY) {
    $runArgs += @("-e", "FLASK_SECRET_KEY=$($env:FLASK_SECRET_KEY)")
}

if ($Detach) {
    $runArgs += "-d"
}

$runArgs += $Image

function Wait-Healthy {
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "$Url/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
            # still starting
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

Write-Host "Starting ${Image} on ${Url} (via wslc) ..."

if ($Detach) {
    & $Wslc @runArgs
    if ($LASTEXITCODE -ne 0) {
        Fail "wslc run failed"
    }
    if (Wait-Healthy) {
        Write-Host "Ready at ${Url}"
    }
    else {
        Write-Host "Container started; health check not ready yet. Try: ${Url}"
    }
    Write-Host "Logs:  ${Wslc} container logs -f ${Name}"
    Write-Host "Stop:  .\aegis-keepass-start-wslc.ps1 -Stop   (or: ${Wslc} container stop ${Name})"
    if ($Open) {
        Start-Process $Url
    }
}
else {
    Write-Host "Open ${Url} in your browser. Press Ctrl+C to stop."
    if ($Open) {
        Start-Job -ScriptBlock {
            param($Target)
            Start-Sleep -Seconds 1
            Start-Process $Target
        } -ArgumentList $Url | Out-Null
    }
    & $Wslc @runArgs
    if ($LASTEXITCODE -ne 0) {
        Fail "wslc run failed"
    }
}
