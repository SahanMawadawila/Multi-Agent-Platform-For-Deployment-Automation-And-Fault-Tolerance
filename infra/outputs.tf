#===============================================================================
# Outputs
#===============================================================================

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

# EKS Outputs
output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "EKS cluster version"
  value       = module.eks.cluster_version
}

# Configure kubectl command
output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

# ArgoCD access
output "argocd_password_command" {
  description = "Command to get ArgoCD initial admin password"
  value       = "kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d"
}

output "argocd_url" {
  description = "ArgoCD URL"
  value       = "http://argocd.${var.domain_name}"
}

# DNS Outputs
output "nameservers" {
  description = "Set these nameservers in your domain registrar (only for DNS owner)"
  value       = var.is_dns_owner ? aws_route53_zone.main[0].name_servers : []
}

output "domain_name" {
  description = "Domain name for the platform"
  value       = var.domain_name
}

output "alb_dns_name" {
  description = "ALB DNS name (for reference)"
  value       = data.aws_lb.shared_alb.dns_name
}

output "acm_certificate_arn" {
  description = "ACM Certificate ARN for HTTPS - Add this to your .env file as ACM_CERTIFICATE_ARN"
  value       = aws_acm_certificate.wildcard.arn
}
