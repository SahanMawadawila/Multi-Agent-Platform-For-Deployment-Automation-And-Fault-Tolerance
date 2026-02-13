param (
    [string]$Region = "ap-south-1"
)

Write-Host "Starting ECR repository cleanup in Region: $Region" -ForegroundColor Cyan

# 1. GET REPOSITORIES
Write-Host "`n--- Retrieving ECR Repositories ---" -ForegroundColor Yellow
$repos = aws ecr describe-repositories --region $Region --query "repositories[].repositoryName" --output json | ConvertFrom-Json

if (-not $repos) {
    Write-Host "No ECR repositories found." -ForegroundColor Green
    exit
}

Write-Host "Found $($repos.Count) repositories."

# 2. DELETE REPOSITORIES
foreach ($repo in $repos) {
    Write-Host "Deleting repository: $repo (forcing image deletion)..."
    try {
        aws ecr delete-repository --repository-name $repo --region $Region --force | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Successfully deleted: $repo" -ForegroundColor Green
        } else {
            Write-Host "Failed to delete: $repo" -ForegroundColor Red
        }
    } catch {
        Write-Host "Error deleting $repo : $_" -ForegroundColor Red
    }
}

Write-Host "`nECR cleanup finished." -ForegroundColor Cyan
