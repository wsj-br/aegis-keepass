# Start Aegis-KeePass OTP Sync from the published Docker image (Windows).
#
# One-liner (PowerShell, defaults):
#   irm https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.ps1 | iex
#
# One-liner with arguments:
#   & ([scriptblock]::Create((irm https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.ps1))) -Detach
#
# Download and run:
#   irm https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.ps1 -OutFile aegis-keepass-start.ps1
#   .\aegis-keepass-start.ps1 -Detach
#   .\aegis-keepass-start.ps1 -Port 9090 -Tag 0.1.1 -Open
#   .\aegis-keepass-start.ps1 -Stop
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
Usage: aegis-keepass-start.ps1 [-Tag TAG] [-Port PORT] [-Name NAME] [-Detach] [-NoPull] [-Open] [-Stop]

Pull and run Aegis-KeePass OTP Sync from ghcr.io (localhost only).

Parameters:
  -Tag TAG       Image tag (default: latest, or `$env:IMAGE_TAG)
  -Port PORT     Host port (default: 8580, or `$env:PORT / `$env:HOST_PORT)
  -Name NAME     Container name (default: aegis-keepass)
  -Detach        Run in the background
  -NoPull        Skip docker pull (use local image if present)
  -Open          Open http://127.0.0.1:<port> in the default browser when ready
  -Stop          Stop and remove the named container, then exit
  -Help          Show this help

Environment:
  IMAGE_REPO, IMAGE_TAG, CONTAINER_NAME, PORT / HOST_PORT
  SESSION_TIMEOUT_SECONDS, MAX_IN_MEMORY_UPLOAD_BYTES, MAX_UPLOAD_BYTES
  FLASK_SECRET_KEY (optional)

Examples:
  irm https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.ps1 | iex
  .\aegis-keepass-start.ps1 -Detach -Port 9090
  .\aegis-keepass-start.ps1 -Tag 0.1.1 -Open
  .\aegis-keepass-start.ps1 -Stop
"@
}

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

function Test-DockerReady {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Fail "Missing required command: docker. Install Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/"
    }
    try {
        docker info 1>$null 2>$null
        if ($LASTEXITCODE -ne 0) {
            Fail "Docker is installed but not running (or not reachable). Start Docker Desktop and try again."
        }
    }
    catch {
        Fail "Docker is installed but not running (or not reachable). Start Docker Desktop and try again."
    }
}

function Test-ContainerExists([string]$ContainerName) {
    $names = docker ps -a --format "{{.Names}}" 2>$null
    return ($names -split "`r?`n") -contains $ContainerName
}

function Stop-AegisContainer([string]$ContainerName) {
    if (Test-ContainerExists $ContainerName) {
        Write-Host "Stopping container '${ContainerName}'..."
        docker stop $ContainerName 1>$null 2>$null | Out-Null
        docker rm $ContainerName 1>$null 2>$null | Out-Null
        Write-Host "Removed '${ContainerName}'."
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

Test-DockerReady

$Image = "${ImageRepo}:${Tag}"
$Url = "http://127.0.0.1:${Port}"

$sessionTimeout = if ($env:SESSION_TIMEOUT_SECONDS) { $env:SESSION_TIMEOUT_SECONDS } else { "1800" }
$maxInMemory = if ($env:MAX_IN_MEMORY_UPLOAD_BYTES) { $env:MAX_IN_MEMORY_UPLOAD_BYTES } else { "33554432" }
$maxUpload = if ($env:MAX_UPLOAD_BYTES) { $env:MAX_UPLOAD_BYTES } else { "52428800" }

if ($Stop) {
    Stop-AegisContainer -ContainerName $Name
    exit 0
}

if (Test-ContainerExists $Name) {
    Write-Host "Removing existing container '${Name}'..."
    docker stop $Name 1>$null 2>$null | Out-Null
    docker rm $Name 1>$null 2>$null | Out-Null
}

if (-not $NoPull) {
    Write-Host "Pulling ${Image}..."
    docker pull $Image
    if ($LASTEXITCODE -ne 0) {
        Fail "docker pull failed for ${Image}"
    }
}

$runArgs = @(
    "run",
    "--name", $Name,
    "--rm",
    # Dual-stack loopback: browsers often try ::1 first for "localhost".
    "-p", "127.0.0.1:${Port}:8580",
    "-p", "[::1]:${Port}:8580",
    "--read-only",
    "--tmpfs", "/tmp:size=64M,mode=1777",
    "-e", "SESSION_TIMEOUT_SECONDS=${sessionTimeout}",
    "-e", "MAX_IN_MEMORY_UPLOAD_BYTES=${maxInMemory}",
    "-e", "MAX_UPLOAD_BYTES=${maxUpload}"
)

if ($env:FLASK_SECRET_KEY) {
    $runArgs += @("-e", "FLASK_SECRET_KEY=$($env:FLASK_SECRET_KEY)")
}

# Always detach so we can wait for /health before opening the UI.
# Foreground mode follows logs until Ctrl+C.
$runArgs += "-d"
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

Write-Host "Starting ${Image} on ${Url} ..."

& docker @runArgs
if ($LASTEXITCODE -ne 0) {
    Fail "docker run failed"
}

if (Wait-Healthy) {
    Write-Host "Ready at ${Url}"
}
else {
    Write-Host "Container started; health check not ready yet. Try: ${Url}"
}

if ($Open) {
    Start-Process $Url
}

if ($Detach) {
    Write-Host "Logs:  docker logs -f ${Name}"
    Write-Host "Stop:  .\aegis-keepass-start.ps1 -Stop   (or: docker stop ${Name})"
}
else {
    Write-Host "Press Ctrl+C to stop."
    try {
        & docker logs -f $Name
    }
    finally {
        docker stop $Name 1>$null 2>$null | Out-Null
    }
}
