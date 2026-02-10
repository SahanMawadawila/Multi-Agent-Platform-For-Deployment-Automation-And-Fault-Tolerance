#===============================================================================
# Outputs for Central DNS Configuration
#===============================================================================

output "zone_id" {
  description = "Route53 Hosted Zone ID"
  value       = aws_route53_zone.main.zone_id
}

output "nameservers" {
  description = <<-EOT
    Set these nameservers in your domain registrar (Namecheap/GoDaddy).
    This is a ONE-TIME setup after initial apply.
  EOT
  value       = aws_route53_zone.main.name_servers
}

output "domain_name" {
  description = "Root domain name"
  value       = var.domain_name
}

output "delegated_subdomains" {
  description = "Currently delegated subdomains"
  value       = keys(var.delegated_subdomains)
}

output "next_steps" {
  description = "Instructions for teammates"
  value       = <<-EOT
    
    === SETUP COMPLETE ===
    
    1. Update your domain registrar with these nameservers (one-time):
       ${join("\n       ", aws_route53_zone.main.name_servers)}
    
    2. For teammates to use their own subdomain:
       a) They create a Route53 hosted zone for "<name>.${var.domain_name}" in their AWS account
       b) They send you the 4 NS records from their zone
       c) You add them to delegated_subdomains variable and run terraform apply
       d) They can then run the main infra with domain_name = "<name>.${var.domain_name}"
    
  EOT
}
