#===============================================================================
# Route 53 DNS Configuration
#===============================================================================

# Local to determine zone_id (either from created zone or external)
locals {
  # Use external zone ID if provided, otherwise use the created zone
  zone_id = var.is_dns_owner ? aws_route53_zone.main[0].zone_id : var.external_zone_id
}

# Hosted Zone - Only created by DNS owner (for backwards compatibility)
# Teammates should use infra/dns/ folder instead and set is_dns_owner = false
resource "aws_route53_zone" "main" {
  count = var.is_dns_owner ? 1 : 0
  name  = var.domain_name

  lifecycle {
    prevent_destroy = false
  }

  tags = {
    Environment = "dev"
    Project     = var.cluster_name
  }
}

# Wildcard DNS record - auto-updates when ALB changes
# Covers ALL subdomains: argocd.domain.com, app1.domain.com, etc.
resource "aws_route53_record" "wildcard" {
  zone_id = local.zone_id
  name    = "*.${var.domain_name}"
  type    = "CNAME"
  ttl     = 60

  records = [data.aws_lb.shared_alb.dns_name]
}

# Data source to get ALB created by AWS LB Controller
data "aws_lb" "shared_alb" {
  tags = {
    "ingress.k8s.aws/stack" = "shared-alb"
  }

  depends_on = [helm_release.argocd]
}

#===============================================================================
# ACM Certificate for HTTPS (Wildcard)
#===============================================================================

# Request wildcard certificate
resource "aws_acm_certificate" "wildcard" {
  domain_name       = "*.${var.domain_name}"
  validation_method = "DNS"

  subject_alternative_names = [var.domain_name] # Also cover root domain

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Environment = "dev"
    Project     = var.cluster_name
  }
}

# Create DNS validation records in Route53
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.wildcard.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = local.zone_id
}

# Wait for certificate validation to complete
resource "aws_acm_certificate_validation" "wildcard" {
  certificate_arn         = aws_acm_certificate.wildcard.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}
