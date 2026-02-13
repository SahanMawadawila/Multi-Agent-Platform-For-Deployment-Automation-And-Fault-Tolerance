$TempPath = "devops_agents/temp"

Write-Host "Starting cleanup of local temp directory: $TempPath" -ForegroundColor Cyan

if (Test-Path $TempPath) {
    $items = Get-ChildItem -Path $TempPath -Recurse
    if ($items) {
        Write-Host "Found $($items.Count) items to delete."
        Remove-Item -Path "$TempPath\*" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Successfully cleaned $TempPath" -ForegroundColor Green
    } else {
        Write-Host "$TempPath is already empty." -ForegroundColor Green
    }
} else {
    Write-Host "Directory $TempPath does not exist." -ForegroundColor Yellow
}

Write-Host "`nLocal temp cleanup finished." -ForegroundColor Cyan
