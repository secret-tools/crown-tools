param([switch]$Setup, [Parameter(ValueFromRemainingArguments=$true)][string[]]$AppArguments)
$ErrorActionPreference = 'Stop'
$env:NO_COLOR = $null
$env:COLORTERM = 'truecolor'
$env:TERM = 'xterm-256color'
$crownApp = Split-Path -Parent $PSScriptRoot
$crownRoot = Split-Path -Parent $crownApp
$crownVenv = Join-Path $crownRoot '.venv\Scripts\python.exe'
$crownExe = $null
foreach ($crownCandidate in @($crownVenv)) {
    if (Test-Path -LiteralPath $crownCandidate) {
        $crownProbe = Start-Process -FilePath $crownCandidate -ArgumentList '-c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"' -WindowStyle Hidden -Wait -PassThru
        if ($crownProbe.ExitCode -eq 0) {$crownExe=$crownCandidate; break}
    }
}
if (-not $crownExe) {
    foreach ($crownCommand in @('py','python')) {
        if (Get-Command $crownCommand -ErrorAction SilentlyContinue) {
            try {
                $crownResult = & $crownCommand -c 'import sys; print(sys.executable); sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>$null
                if ($LASTEXITCODE -eq 0) {$crownExe=$crownResult.Trim(); break}
            } catch {continue}
        }
    }
}
if (-not $crownExe) {Write-Host 'Python absent ou environnement .venv invalide. Installez Python 3.12+ depuis python.org, puis lancez setup.bat.'; exit 1}
& $crownExe -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'
if ($LASTEXITCODE -ne 0) {Write-Host 'Python 3.12+ requis.'; exit 1}
$crownNeedsSetup = $Setup -or (-not (Test-Path -LiteralPath $crownVenv))
if (-not $crownNeedsSetup) {
    & $crownExe (Join-Path $PSScriptRoot 'setup_modules.py') --check *> $null
    $crownNeedsSetup = $LASTEXITCODE -ne 0
}
if ($crownNeedsSetup) {
    if (-not $Setup) {Write-Host 'Premier lancement / First launch: installation des dependances Python...'}
    if (-not (Test-Path $crownVenv)) {
        & $crownExe -m venv (Join-Path $crownRoot '.venv')
        if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
    }
    $setupScript = Join-Path $PSScriptRoot 'setup_modules.py'
    if (Test-Path $setupScript) {
        & $crownVenv $setupScript
    } else {
        & $crownVenv -m pip --version
        & $crownVenv -m pip install --disable-pip-version-check --no-compile --prefer-binary -r (Join-Path $crownApp 'requirements.txt')
    }
    if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
    if ($Setup) {exit 0}
    $crownExe = $crownVenv
}
& $crownExe (Join-Path $crownApp 'main.py') @AppArguments
exit $LASTEXITCODE
