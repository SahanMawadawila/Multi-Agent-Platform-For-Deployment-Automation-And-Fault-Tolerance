# Get the script's directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
# Navigate to project root (assuming script is in infra/clean_up)
$ProjectRoot = Resolve-Path "$ScriptDir/../../"
Push-Location $ProjectRoot

Write-Host "Project Root: $ProjectRoot" -ForegroundColor Cyan

# Define venv path
$VenvPath = "$ProjectRoot/backend/.venv"
$ActivateScript = "$VenvPath/Scripts/Activate.ps1"

# Check if venv exists
if (Test-Path $ActivateScript) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & $ActivateScript
} else {
    Write-Host "Virtual environment not found at $VenvPath. Trying to run with system Python..." -ForegroundColor Yellow
}

# Run the reset script
$ResetScript = "backend/reset_db.py"
if (Test-Path $ResetScript) {
    Write-Host "Running database reset script..." -ForegroundColor Cyan
    python $ResetScript
} else {
    Write-Host "Error: $ResetScript not found!" -ForegroundColor Red
}

# Return to original location
Pop-Location
Write-Host "`nDatabase cleanup finished." -ForegroundColor Cyan
