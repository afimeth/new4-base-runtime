$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try { & python app.py serve; if ($LASTEXITCODE -ne 0) { throw 'Runtime startup failed' } }
finally { Pop-Location }
