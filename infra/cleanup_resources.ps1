param (
    [string]$VpcName = "Flow-Pilot-AI-vpc",
    [string]$Region = "ap-south-1"
)

Write-Host "Starting cleanup for VPC Name: $VpcName in Region: $Region" -ForegroundColor Cyan

# 0. GET VPC ID
Write-Host "`n--- Retrieving VPC ID ---" -ForegroundColor Yellow

$ids = aws ec2 describe-vpcs --filters "Name=tag:Name,Values=$VpcName" --region $Region --query "Vpcs[].VpcId" --output json | ConvertFrom-Json

if (-not $ids) {
    Write-Host "No VPC found with Name '$VpcName'" -ForegroundColor Red
    exit
}

$VpcId = $ids[0]
Write-Host "Found VPC ID: $VpcId" -ForegroundColor Green

# 1. DELETE LOAD BALANCERS
Write-Host "`n--- Checking for Load Balancers ---" -ForegroundColor Yellow
$lbs = aws elbv2 describe-load-balancers --region $Region --query "LoadBalancers[?VpcId=='$VpcId'].LoadBalancerArn" --output json | ConvertFrom-Json

if ($lbs) {
    foreach ($lbArn in $lbs) {
        Write-Host "Deleting Load Balancer: $lbArn"
        aws elbv2 delete-load-balancer --load-balancer-arn $lbArn --region $Region
    }
    Write-Host "Waiting 15 seconds for LBs to delete..."
    Start-Sleep -Seconds 15
} else {
    Write-Host "No Load Balancers found."
}

# 2. SECURITY GROUPS - RECURSIVE DELETE
Write-Host "`n--- Cleaning Security Groups ---" -ForegroundColor Yellow

# Try multiple passes to resolve dependencies
$maxRetries = 10
for ($i = 0; $i -lt $maxRetries; $i++) {
    $sgs = aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VpcId" --region $Region --query "SecurityGroups[?GroupName!='default'].GroupId" --output json | ConvertFrom-Json
    
    if (-not $sgs) {
        Write-Host "All non-default security groups deleted!" -ForegroundColor Green
        break
    }

    foreach ($sg in $sgs) {
        Write-Host "Attempting delete: $sg"
        aws ec2 delete-security-group --group-id $sg --region $Region 2>$null
    }
    Start-Sleep -Seconds 2
}

Write-Host "`nCleanup script execution finished." -ForegroundColor Cyan
