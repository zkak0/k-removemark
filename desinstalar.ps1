#Requires -Version 5.1
# Desinstalador (Windows): elimina todo lo que instalo k-removemark.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File desinstalar.ps1
#
# No borra el repositorio clonado ni Python; solo lo copiado a los asistentes.

$ErrorActionPreference = "Continue"

$skills = @("remove-ai-marks", "clean-user-facing-text")

$dests = @(
    (Join-Path $env:USERPROFILE ".config\opencode\skills"),
    (Join-Path $env:USERPROFILE ".claude\skills"),
    (Join-Path $env:USERPROFILE ".cursor\skills"),
    (Join-Path $env:USERPROFILE ".gemini\antigravity\skills"),
    (Join-Path $env:USERPROFILE ".gemini\skills"),
    (Join-Path $env:USERPROFILE ".copilot\skills"),
    (Join-Path $env:USERPROFILE ".codex\skills")
)

foreach ($dest in $dests) {
    foreach ($s in $skills) {
        $p = Join-Path $dest $s
        if (Test-Path $p) {
            Remove-Item $p -Recurse -Force
            Write-Host "eliminado: $p"
        }
    }
}

$rules = Join-Path $env:USERPROFILE ".cursor\rules"
if (Test-Path $rules) {
    Get-ChildItem $rules -Filter "*remove-ai-marks*" -ErrorAction SilentlyContinue | Remove-Item -Force
}

# Quitar el conector MCP de Claude Desktop si existe
$claudeConfigFile = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
if (Test-Path $claudeConfigFile) {
    try {
        $config = Get-Content $claudeConfigFile -Raw | ConvertFrom-Json
        if ($null -ne $config.mcpServers."k-removemark") {
            $config.mcpServers.PSObject.Properties.Remove("k-removemark")
            $configJson = ConvertTo-Json $config -Depth 10
            Set-Content -Path $claudeConfigFile -Value $configJson -Encoding UTF8
            Write-Host "conector MCP eliminado de Claude Desktop"
        }
    } catch {
        Write-Warning "no se pudo actualizar claude_desktop_config.json"
    }
}

# Detener el servicio HTTP local si esta corriendo
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "server\.py" -and $_.CommandLine -match "service" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "servicio HTTP detenido (si estaba corriendo)"

Write-Host ""
Write-Host "Desinstalacion completa. Reinicia tus asistentes de IA."
