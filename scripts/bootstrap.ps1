# LOCATION³ one-line start for Windows PowerShell.
#
#   $env:LOCATION3_AGENT = "claude"; irm https://raw.githubusercontent.com/lukexyz/location-location-location/main/scripts/bootstrap.ps1 | iex
#
# Clones the repository, installs its Python and Node dependencies, reports what
# it found on this machine, and opens the chosen coding agent inside the
# repository with the research skill loaded. It never asks for, reads out, or
# stores a routing key; it only reports whether ORS_API_KEY is set.
#
# Environment overrides (all optional):
#   LOCATION3_AGENT   claude | codex (required when piped through iex)
#   LOCATION3_DIR     where to clone; default .\location-location-location
#   LOCATION3_REPO    clone source; default the GitHub repository
#   LOCATION3_LAUNCH  set to 0 to stop after installing instead of opening the agent
$ErrorActionPreference = "Stop"

$agent = if ($env:LOCATION3_AGENT) { $env:LOCATION3_AGENT.Trim().ToLowerInvariant() } else { "" }
$target = if ($env:LOCATION3_DIR) { $env:LOCATION3_DIR } else { "location-location-location" }
$repo = if ($env:LOCATION3_REPO) { $env:LOCATION3_REPO } else { "https://github.com/lukexyz/location-location-location.git" }
$launch = if ($env:LOCATION3_LAUNCH) { $env:LOCATION3_LAUNCH } else { "1" }

function Fail([string] $message) { Write-Host "bootstrap: $message" -ForegroundColor Red; throw $message }
function Have([string] $name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

switch ($agent) {
  "claude" { }
  "codex" { }
  "" { Fail 'name the agent to open first: $env:LOCATION3_AGENT = "claude"   or   "codex"' }
  default { Fail "unknown agent '$agent'; use claude or codex" }
}

Write-Host "LOCATION3 bootstrap"
Write-Host "  agent      $agent"
Write-Host "  directory  $target"

# ---- prerequisites --------------------------------------------------------------
$missing = @()
if (Have git) { Write-Host "  git        found" } else { Write-Host "  git        MISSING  https://git-scm.com/downloads"; $missing += "git" }
if (Have uv) { Write-Host "  uv         found (installs Python 3.11+ itself)" } else { Write-Host "  uv         MISSING  irm https://astral.sh/uv/install.ps1 | iex"; $missing += "uv" }
if (Have node) {
  $nodeMajor = 0
  try { $nodeMajor = [int](& node -p 'process.versions.node.split(".")[0]') } catch { $nodeMajor = 0 }
  if ($nodeMajor -ge 22) { Write-Host "  node       found (v$nodeMajor)" } else { Write-Host "  node       TOO OLD (v$nodeMajor; need 22+)  https://nodejs.org"; $missing += "node" }
} else { Write-Host "  node       MISSING  https://nodejs.org (22 or newer)"; $missing += "node" }
if (Have npm) { Write-Host "  npm        found" } else { Write-Host "  npm        MISSING  ships with Node"; $missing += "npm" }
$agentFound = Have $agent
if ($agentFound) { Write-Host ("  {0,-10} found" -f $agent) }
elseif ($agent -eq "claude") { Write-Host "  claude     not on PATH  npm install -g @anthropic-ai/claude-code" }
else { Write-Host "  codex      not on PATH  npm install -g @openai/codex" }
if ($env:ORS_API_KEY) {
  Write-Host "  ORS_API_KEY  set (never printed; the run gets a real drive-time boundary)"
} else {
  Write-Host "  ORS_API_KEY  not set  the first run uses a labelled distance boundary; a free key from https://openrouteservice.org upgrades it"
}
if ($missing.Count -gt 0) { Fail "install the missing tools ($($missing -join ', ')) and paste the line again" }

# ---- clone or reuse ---------------------------------------------------------------
if (Test-Path (Join-Path $target ".git")) {
  Write-Host "Using the existing clone at $target (not pulled; run git pull yourself if you want the latest)"
} elseif (Test-Path $target) {
  Fail "$target exists and is not a git clone; set LOCATION3_DIR to another folder"
} else {
  Write-Host "Cloning $repo"
  & git clone --quiet $repo $target
  if ($LASTEXITCODE -ne 0) { Fail "git clone failed" }
}
Set-Location $target

# ---- install ----------------------------------------------------------------------
Write-Host "Installing Python dependencies (uv sync)"
& uv sync --quiet
if ($LASTEXITCODE -ne 0) { Fail "uv sync failed" }
Write-Host "Installing viewer dependencies (npm install)"
& npm install --no-fund --no-audit --loglevel=error
if ($LASTEXITCODE -ne 0) { Fail "npm install failed" }

Write-Host ""
Write-Host "Ready. Everything researched here stays in gitignored folders under $(Get-Location)."
$prompt = "Use the location-research skill to help me run my own bounded location search, previewing every outbound call before it happens."
if ($launch -eq "0") {
  Write-Host "Not launching (LOCATION3_LAUNCH=0). To start: cd `"$target`"; $agent `"$prompt`""
  return
}
if (-not $agentFound) {
  Write-Host "Install $agent, then run:  cd `"$target`"; $agent `"$prompt`""
  return
}
Write-Host "Opening $agent with the research skill loaded"
& $agent $prompt
