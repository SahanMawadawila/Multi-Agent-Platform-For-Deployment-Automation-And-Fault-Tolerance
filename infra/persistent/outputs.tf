#===============================================================================
# Outputs — Copy these values to your main infra stack variables
#===============================================================================

output "nameservers" {
  description = "Set these nameservers in Namecheap (ONE TIME ONLY)"
  value       = aws_route53_zone.main.name_servers
}

output "zone_id" {
  description = "Route53 Zone ID — use this as 'route53_zone_id' in the main infra stack"
  value       = aws_route53_zone.main.zone_id
}

output "acm_certificate_arn" {
  description = "ACM Certificate ARN — use this as 'acm_certificate_arn' in the main infra stack and in devops_agents .env"
  value       = aws_acm_certificate.wildcard.arn
}

output "domain_name" {
  description = "Domain name for reference"
  value       = var.domain_name
}
