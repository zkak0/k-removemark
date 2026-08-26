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
$Root = (Resolve-Path (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
$Skills = @("remove-ai-marks", "clean-user-facing-text")

# Comprobación e instalación silenciosa de Python si falta (Windows)
$hasPython = $false
try {
    $pyVer = & python --version 2>$null
    if ($pyVer) { $hasPython = $true }
} catch {}

if (-not $hasPython) {
    Write-Host "Python 3 no está instalado. Intentando instalar Python 3.12 de forma silenciosa..."
    try {
        & winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements | Out-Null
        Write-Host "Python se ha instalado correctamente. Es posible que debas reiniciar tu asistente de IA para que lo detecte."
    } catch {
        Write-Warning "No se pudo instalar Python automáticamente mediante winget. Por favor, instálalo manualmente desde https://python.org"
    }
}

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
Write-Host "Listo. Reiniciá tu asistente de IA para que cargue las habilidades."
Write-Host "Si el servicio HTTP local no está corriendo, la habilidad te indicará"
Write-Host "cómo iniciarlo (python service\scripts\server.py)."

# Autoconfiguración automática para Claude Desktop (servidor MCP) si está instalado
$claudeConfigDir = Join-Path $env:APPDATA "Claude"
$claudeConfigFile = Join-Path $claudeConfigDir "claude_desktop_config.json"
if (Test-Path $claudeConfigDir) {
    Write-Host "`nConfigurando conector MCP para Claude Desktop de forma automática..."
    $mcpPath = Join-Path $Root "service\scripts\mcp_server.py"

    $config = @{ mcpServers = @{} }
    if (Test-Path $claudeConfigFile) {
        try {
            $config = Get-Content $claudeConfigFile -Raw | ConvertFrom-Json
        } catch {
            Write-Warning "No se pudo leer claude_desktop_config.json, se creará uno nuevo."
        }
    }
    if ($null -eq $config.mcpServers) {
        $config.mcpServers = @{}
    }
    $mcpEntry = @{ command = "python"; args = @($mcpPath) }
    $mcpEnv = @{}
    if ($env:WATERMARKS_SERVER_PORT) {
        $mcpEnv["WATERMARKS_SERVER_PORT"] = $env:WATERMARKS_SERVER_PORT
        $mcpEnv["WATERMARKS_SERVER_URL"] = "http://127.0.0.1:$($env:WATERMARKS_SERVER_PORT)"
    }
    if ($env:WATERMARKS_SERVER_API_KEY) { $mcpEnv["WATERMARKS_SERVER_API_KEY"] = $env:WATERMARKS_SERVER_API_KEY }
    if ($mcpEnv.Count -gt 0) { $mcpEntry.env = $mcpEnv }
    $config.mcpServers."k-removemark" = $mcpEntry
    $configJson = ConvertTo-Json $config -Depth 10
    Set-Content -Path $claudeConfigFile -Value $configJson -Encoding UTF8
    Write-Host "Conector MCP de Claude Desktop configurado con éxito."
}

# Precalentar el servicio HTTP para que la primera llamada sea instantánea
Write-Host ""
Write-Host "Precalentando servicio HTTP local..."
try {
    $pyExe = "python"
    try { & python --version 2>$null | Out-Null } catch { $pyExe = "python3" }
    $svcPort = if ($env:WATERMARKS_SERVER_PORT) { $env:WATERMARKS_SERVER_PORT } else { "8765" }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $pyExe
    $psi.Arguments = "service\scripts\server.py"
    $psi.WorkingDirectory = $Root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    if ($env:WATERMARKS_SERVER_PORT) { $psi.EnvironmentVariables["WATERMARKS_SERVER_PORT"] = $env:WATERMARKS_SERVER_PORT }
    if ($env:WATERMARKS_SERVER_API_KEY) { $psi.EnvironmentVariables["WATERMARKS_SERVER_API_KEY"] = $env:WATERMARKS_SERVER_API_KEY }
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Start-Sleep -Milliseconds 800
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$svcPort/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { Write-Host "Servicio HTTP listo en http://127.0.0.1:$svcPort" }
    } catch {}
} catch {
    Write-Host "El servicio se iniciara bajo demanda."
}
Write-Host ""
Write-Host "(opcional) Para proteger el servicio HTTP local de accesos no autorizados,"
Write-Host "podés setear la variable WATERMARKS_SERVER_API_KEY antes de la instalacion:"
Write-Host "  $env:WATERMARKS_SERVER_API_KEY='tu-clave-secreta'; .\install.ps1"