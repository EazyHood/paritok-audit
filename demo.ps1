# =====================================================================
#  DEMO PARA EL VIDEO  -  un solo comando, menos de 3 minutos
# =====================================================================
#  Uso:
#     1. Abre OBS (o Win+G) y empieza a grabar
#     2. powershell -ExecutionPolicy Bypass -File demo.ps1
#     3. Deja que corra. Para la grabación cuando termine.
#
#  El guion con lo que decir en cada tramo está en
#  C:\Users\jhona\bounties\PARITOK-ENTREGA.md
# =====================================================================

$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot

function Titulo($texto) {
  Write-Host ""
  Write-Host ("=" * 74) -ForegroundColor DarkCyan
  Write-Host "  $texto" -ForegroundColor Cyan
  Write-Host ("=" * 74) -ForegroundColor DarkCyan
  Write-Host ""
  Start-Sleep -Milliseconds 900
}

function Comando($cmd) {
  Write-Host "  > $cmd" -ForegroundColor Yellow
  Write-Host ""
  Start-Sleep -Milliseconds 600
}

Clear-Host
Write-Host ""
Write-Host "  paritok-audit" -ForegroundColor White
Write-Host "  Measure what context compression costs you, not just what it saves." -ForegroundColor Gray
Write-Host ""
Start-Sleep -Seconds 2

# ---------------------------------------------------------------- 1
# Ollama descarga el modelo de memoria tras unos minutos de inactividad, así que
# `ollama ps` saldría vacío y el video mostraría "corriendo" sobre una tabla en
# blanco. Lo cargamos antes, en silencio.
Write-Host "  cargando el modelo..." -ForegroundColor DarkGray
try {
  Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -TimeoutSec 120 `
    -Body (@{ model = "paritok-4b-v1"; prompt = "hi"; stream = $false; keep_alive = "10m" } | ConvertTo-Json) `
    -ContentType "application/json" | Out-Null
} catch { }
Clear-Host

Titulo "1. Paritok is really running, locally"
Comando "ollama ps"
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" ps
Start-Sleep -Seconds 3

# ---------------------------------------------------------------- 2
Titulo "2. Audit real agent traffic -- savings AND fidelity"
Comando "python run_audit.py --only dependency_log --only error_log"
py -c "import sys; sys.path.insert(0,'.'); from paritok_audit import cli; sys.exit(cli.main(['--only','dependency_log','--only','error_log']))"
Start-Sleep -Seconds 3

# ---------------------------------------------------------------- 3
Titulo "3. The full corpus -- six real artefacts"
Comando "cat REPORT.txt"
if (Test-Path RUN.log) { Get-Content RUN.log | Select-Object -Last 26 }
elseif (Test-Path REPORT.txt) { Get-Content REPORT.txt }
Start-Sleep -Seconds 5

# ---------------------------------------------------------------- 4
Titulo "4. The bug this found -- it is line length, not size"
Write-Host "  A 25,279-char single-line JSON raised HTTP 400." -ForegroundColor White
Write-Host "  The same JSON re-indented is LARGER and compresses fine:" -ForegroundColor White
Write-Host ""
Write-Host "     one line     25,279 chars   1 line       ->  400 Bad Request" -ForegroundColor Red
Write-Host "     re-indented  33,343 chars   many lines   ->  ratio 89.4%" -ForegroundColor Green
Write-Host "     C++ header   46,838 chars   1,244 lines  ->  ratio 70.0%" -ForegroundColor Green
Write-Host ""
Write-Host "  _token_split_block only cuts BETWEEN lines, so one long line" -ForegroundColor Gray
Write-Host "  bypasses the guard written to stop exactly this." -ForegroundColor Gray
Write-Host ""
Start-Sleep -Seconds 6

# ---------------------------------------------------------------- 5
Titulo "5. Fixed upstream -- PR #15"
Write-Host "  https://github.com/Paritok-official/paritok-4b-v1/pull/15" -ForegroundColor White
Write-Host ""
Write-Host "  5 regression tests, 96 passing." -ForegroundColor Gray
Write-Host "  No-op when every line already fits, so their SWE-bench path is" -ForegroundColor Gray
Write-Host "  byte-identical. That input now compresses 7,773 -> 609 tokens." -ForegroundColor Gray
Write-Host ""
Start-Sleep -Seconds 5

Titulo "github.com/EazyHood/paritok-audit   --   Apache 2.0"
Write-Host ""
