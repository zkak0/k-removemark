#Requires -Version 5.1
# One-command installer (Windows): copy the skills into whichever AI agent you use.
#
#   .\install.ps1                 # detect host agent(s) and install
#   .\install.ps1 -Target cursor  # force: opencode|claude-code|cursor|
#                                 #   antigravity|gemini-cli|copilot|codex|all
#   .\install.ps1 -List           # show the paths it would use
#
# No network, no node, no python needed: it only copies directories.

param(
    [string]$Target = "auto",
    [switch]$List
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Skills = @("remove-ai-marks", "clean-user-facing-text")

function Get-SkillDest([string]$agent) {
    switch ($agent) {
        "opencode"     { return Join-Path $env:USERPROFILE ".config\opencode\skills" }
        "claude-code"  { return Join-Path $env:USERPROFILE ".claude\skills" }
        "cursor"       { return Join-Path $env:USERPROFILE ".cursor\skills" }
        "antigravity"  { return Join-Path $env:USERPROFILE ".gemini\antigravity\skills" }
        "gemini-cli"   { return Join-Path $env:USERPROFILE ".gemini\skills" }
        "copilot"      { return Join-Path $env:USERPROFILE ".copilot\skills" }
        "codex"        { return Join-Path $env:USERPROFILE ".codex\skills" }
        default        { return "" }
    }
}

function Get-Agents {
    $found = @()
    if (Test-Path "$env:USERPROFILE\.claude") { $found += "claude-code" }
    if (Test-Path "$env:USERPROFILE\.cursor") { $found += "cursor" }
    if (Test-Path "$env:USERPROFILE\.config\opencode") { $found += "opencode" }
    if (Test-Path "$env:USERPROFILE\.gemini\antigravity") { $found += "antigravity" }
    if (Test-Path "$env:USERPROFILE\.gemini") { $found += "gemini-cli" }
    if (Test-Path "$env:USERPROFILE\.copilot") { $found += "copilot" }
    if (Test-Path "$env:USERPROFILE\.codex") { $found += "codex" }
    return $found
}

if ($List) {
    foreach ($a in @("opencode", "claude-code", "cursor", "antigravity", "gemini-cli", "copilot", "codex")) {
        Write-Output "$a -> $(Get-SkillDest $a)"
    }
    exit 0
}

$agents = @()
if ($Target -eq "auto") {
    $agents = @(Get-Agents)
    if ($agents.Count -eq 0) {
        Write-Host "No agent config dir found. Run:  .\install.ps1 -List"
        Write-Host "Then force a target, e.g.:  .\install.ps1 -Target cursor"
        exit 1
    }
} elseif ($Target -eq "all") {
    $agents = @("opencode", "claude-code", "cursor", "antigravity", "gemini-cli", "copilot", "codex")
} else {
    $agents = @($Target)
}

$installed = $false
foreach ($agent in $agents) {
    $dest = Get-SkillDest $agent
    if (-not $dest) {
        Write-Host "unknown target: $agent"
        continue
    }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    foreach ($s in $Skills) {
        $src = Join-Path $Root "skills\$s"
        if (Test-Path $src) {
            Copy-Item $src (Join-Path $dest $s) -Recurse -Force
            Write-Host "installed skill '$s' -> $dest\$s"
            $installed = $true
        }
    }
    if ($agent -eq "cursor" -and (Test-Path (Join-Path $Root "integrations\cursor"))) {
        $rules = Join-Path $env:USERPROFILE ".cursor\rules"
        New-Item -ItemType Directory -Force -Path $rules | Out-Null
        Copy-Item (Join-Path $Root "integrations\cursor\*.mdc") $rules -Force
        Write-Host "installed Cursor rules -> $rules"
    }
}

if (-not $installed) {
    Write-Host "nothing installed (no skills found?)"
    exit 1
}

Write-Host ""
Write-Host "Done. Restart your agent. If the local HTTP service is not running,"
Write-Host "the skill will tell you how to start it (make serve / docker compose up -d)."