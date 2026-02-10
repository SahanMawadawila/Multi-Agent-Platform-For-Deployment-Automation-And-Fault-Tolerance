#Apply terraform 
terraform apply -auto-approve

#Destroy terraform
terraform destroy -auto-approve

after apply following command must be run to update kubeconfig
aws eks update-kubeconfig --region ap-south-1 --name Flow-Pilot-AI

when destroying following points terrform get stucked then run following commands.

1) module.vpc.aws_internet_gateway.this[0]: Still destroying.

solution ->
# List load balancers
aws elbv2 describe-load-balancers --region ap-south-1 --no-cli-pager --query "LoadBalancers[].{Name:LoadBalancerName,ARN:LoadBalancerArn}" --output table

# Delete each one
aws elbv2 delete-load-balancer --load-balancer-arn <ARN> --region ap-south-1


2) module.vpc.aws_vpc.this[0]: Still destroying... [id=vpc-0ba9cbaa41c1e8b4a, 00m10s elapsed]

solution -> aws ec2 describe-security-groups --filters "Name=vpc-id,Values=vpc-0a4935f6b417e3e75" --region ap-south-1 --no-cli-pager --query "SecurityGroups[].{ID:GroupId,Name:GroupName}" --output table

aws ec2 delete-security-group --group-id <SG_ID> --region ap-south-1 ( dont delete default)