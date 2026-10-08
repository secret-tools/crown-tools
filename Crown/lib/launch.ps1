param([switch]$Setup, [Parameter(ValueFromRemainingArguments=$true)][string[]]$AppArguments)
$ErrorActionPreference = 'Stop'
$env:NO_COLOR = $null
$env:COLORTERM = 'truecolor'
$env:TERM = 'xterm-256color'
$crownApp = Split-Path -Parent $PSScriptRoot
$crownRoot = Split-Path -Parent $crownApp
$crownVenvDir = Join-Path $crownRoot '.venv'
$crownVenv = Join-Path $crownVenvDir 'Scripts\python.exe'
function Test-CrownPython([string]$Executable) {
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable)) {return $false}
    try {
        & $Executable -I -c 'import sys,struct; sys.exit(0 if (3,12) <= sys.version_info[:2] <= (3,14) and struct.calcsize(chr(80))==8 else 1)' *> $null
        return $LASTEXITCODE -eq 0
    } catch {return $false}
}
function Save-CrownDownload([string]$Url, [string]$Destination, [string]$Sha256) {
    if (Test-Path -LiteralPath $Destination) {
        if ((Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -eq $Sha256) {return}
    }
    for ($crownAttempt = 1; $crownAttempt -le 3; $crownAttempt++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Destination
            if ((Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -ne $Sha256) {throw 'Download checksum mismatch.'}
            return
        } catch {
            if ($crownAttempt -eq 3) {throw}
        }
    }
}
function Install-CrownPortablePip {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $crownCache = Join-Path $crownRoot '.python-download'
    $crownSite = Join-Path $crownVenvDir 'Scripts\Lib\site-packages'
    New-Item -ItemType Directory -Force -Path $crownCache, $crownSite | Out-Null
    @('python313.zip','.', '..\..\Crown', 'Lib\site-packages','import site') | Set-Content -LiteralPath (Join-Path $crownVenvDir 'Scripts\python313._pth') -Encoding ascii
    $crownPipMetadata = Invoke-RestMethod -Uri 'https://pypi.org/pypi/pip/25.3/json'
    $crownPipWheel = $crownPipMetadata.urls | Where-Object { $_.filename -eq 'pip-25.3-py3-none-any.whl' } | Select-Object -First 1
    if (-not $crownPipWheel -or -not $crownPipWheel.url.StartsWith('https://files.pythonhosted.org/')) {throw 'Invalid pip download metadata.'}
    $crownPipArchive = Join-Path $crownCache 'pip-25.3.zip'
    Save-CrownDownload $crownPipWheel.url $crownPipArchive $crownPipWheel.digests.sha256
    Expand-Archive -LiteralPath $crownPipArchive -DestinationPath $crownSite -Force
}
try {
    $crownExe = $null
    if (Test-CrownPython $crownVenv) {$crownExe = $crownVenv}
    if (-not $crownExe) {
        foreach ($crownVersion in @('3.13','3.12','3.14')) {
            if (Get-Command py -ErrorAction SilentlyContinue) {
                try {
                    $crownResult = & py "-$crownVersion" -I -c 'import sys; print(sys.executable)' 2>$null
                    if ($LASTEXITCODE -eq 0 -and (Test-CrownPython "$crownResult")) {$crownExe = "$crownResult"; break}
                } catch {}
            }
        }
    }
    if (-not $crownExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
        try {
            $crownResult = & python -I -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and (Test-CrownPython "$crownResult")) {$crownExe = "$crownResult"}
        } catch {}
    }
    if (-not (Test-CrownPython $crownVenv)) {
        if (Test-Path -LiteralPath $crownVenvDir) {
            $crownBackup = Join-Path $crownRoot ('.venv-backup-' + [guid]::NewGuid().ToString('N'))
            Move-Item -LiteralPath $crownVenvDir -Destination $crownBackup
            Write-Host 'Previous environment preserved; creating a compatible environment.'
        }
        if ($crownExe) {
            & $crownExe -m venv $crownVenvDir
            if ($LASTEXITCODE -ne 0) {throw 'Could not create the Python environment.'}
        } else {
            Write-Host 'Preparing portable Python / Preparation automatique de Python...'
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $crownCache = Join-Path $crownRoot '.python-download'
            New-Item -ItemType Directory -Force -Path $crownCache | Out-Null
            $crownArchive = Join-Path $crownCache 'python-3.13.12-embed-amd64.zip'
            Save-CrownDownload 'https://www.python.org/ftp/python/3.13.12/python-3.13.12-embed-amd64.zip' $crownArchive '76f238f606250c87c6beac75dccd35ee99070a13490555936abb6cb64ecce3d0'
            $crownRuntime = Join-Path $crownVenvDir 'Scripts'
            Expand-Archive -LiteralPath $crownArchive -DestinationPath $crownRuntime -Force
            $crownSite = Join-Path $crownRuntime 'Lib\site-packages'
            New-Item -ItemType Directory -Force -Path $crownSite | Out-Null
            @('python313.zip','.', '..\..\Crown', 'Lib\site-packages','import site') | Set-Content -LiteralPath (Join-Path $crownRuntime 'python313._pth') -Encoding ascii
            Install-CrownPortablePip
        }
        if (-not (Test-CrownPython $crownVenv)) {throw 'Python environment verification failed. Run setup.bat again.'}
    }
    & $crownVenv -m pip --version *> $null
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path -LiteralPath (Join-Path $crownVenvDir 'Scripts\python313._pth')) {
            Install-CrownPortablePip
        } else {
            & $crownVenv -m ensurepip --upgrade
            if ($LASTEXITCODE -ne 0) {throw 'pip repair failed. Run setup.bat again.'}
        }
        & $crownVenv -m pip --version *> $null
        if ($LASTEXITCODE -ne 0) {throw 'pip repair could not be verified.'}
    }
    & $crownVenv (Join-Path $PSScriptRoot 'setup_modules.py')
    if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
    if ($Setup) {exit 0}
    & $crownVenv (Join-Path $crownApp 'main.py') @AppArguments
    exit $LASTEXITCODE
} catch {
    Write-Host ('Setup failed / Installation impossible: ' + $_.Exception.Message + ' Check your connection and run setup.bat again.') -ForegroundColor Red
    exit 1
}
