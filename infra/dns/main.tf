#===============================================================================
# Central DNS Configuration
# Run this ONCE by the DNS owner. Others use subdomain delegation.
#===============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

#===============================================================================
# Route 53 Hosted Zone - Created once, shared via subdomain delegation
#===============================================================================

resource "aws_route53_zone" "main" {
  name = var.domain_name

  lifecycle {
    prevent_destroy = true  # Protect from accidental deletion
  }

  tags = {
    Environment = "shared"
    Project     = "Flow-Pilot-AI"
    ManagedBy   = "dns-owner"
  }
}

#===============================================================================
# Subdomain Delegation Records
# Add NS records to delegate subdomains to teammates' hosted zones
#===============================================================================

resource "aws_route53_record" "delegation" {
  for_each = var.delegated_subdomains

  zone_id = aws_route53_zone.main.zone_id
  name    = each.key
  type    = "NS"
  ttl     = 300
  records = each.value
}
