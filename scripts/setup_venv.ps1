# setup_venv.ps1 - create the project venv (.venv) and install requirements.txt.
# Lives in scripts\. Run from anywhere, without changing the machine's execution policy:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_venv.ps1
$ErrorActionPreference = "Stop"
$Want = "3.14"   # project Python version (docs/decisions/0008)

# Work from the repo root (the folder above scripts\); put the caller back where they were afterward.
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    # Only use the py launcher with an explicit version. A bare "python" can be the
    # Microsoft Store 3.12 or the Store's install stub (see 0008).
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw "The py launcher was not found. Install Python $Want from python.org (it includes py)."
    }
    if (-not (Test-Path requirements.txt)) {
        throw "requirements.txt not found in $(Get-Location)."
    }

    $venvPy = ".\.venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        Write-Host ".venv already exists; reusing it. Delete .venv to start over."
    } else {
        & py "-$Want" -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Creating .venv with Python $Want failed. See what is installed with: py --list"
        }
    }

    & $venvPy -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Installing requirements failed." }

    Write-Host ""
    Write-Host "Done. To activate:"
    Write-Host "  PowerShell:  .\.venv\Scripts\Activate.ps1"
    Write-Host "  Git Bash:    source .venv/Scripts/activate"
}
finally {
    Pop-Location
}
