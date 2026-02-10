# Infrastructure (Terraform)

## Prerequisites

Before applying, run the **persistent DNS stack** first (one-time):
```bash
cd infra/persistent
terraform init
terraform apply
```
See [persistent/README.md](persistent/README.md) for full setup instructions.

## Apply Infrastructure

Create `infra/terraform.tfvars` with values from the persistent stack (one-time, gitignored):
```hcl
route53_zone_id     = "<ZONE_ID>"       # from: cd persistent && terraform output zone_id
acm_certificate_arn = "<ACM_ARN>"       # from: cd persistent && terraform output acm_certificate_arn
```

Then apply:
```bash
cd infra
terraform apply
```

After apply, update kubeconfig:
```bash
aws eks update-kubeconfig --region ap-south-1 --name Flow-Pilot-AI
```

## Destroy Infrastructure

```bash
terraform destroy -auto-approve
```

> DNS zone and ACM certificate are safe — they live in `infra/persistent/`.

## Troubleshooting

### 1) `module.vpc.aws_internet_gateway.this[0]`: Still destroying

```bash
# List load balancers
aws elbv2 describe-load-balancers --region ap-south-1 --no-cli-pager \
  --query "LoadBalancers[].{Name:LoadBalancerName,ARN:LoadBalancerArn}" --output table

# Delete each one
aws elbv2 delete-load-balancer --load-balancer-arn <ARN> --region ap-south-1
```

### 2) `module.vpc.aws_vpc.this[0]`: Still destroying

```bash
aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=<VPC_ID>" \
  --region ap-south-1 --no-cli-pager \
  --query "SecurityGroups[].{ID:GroupId,Name:GroupName}" --output table

# Delete each (don't delete default)
aws ec2 delete-security-group --group-id <SG_ID> --region ap-south-1
```