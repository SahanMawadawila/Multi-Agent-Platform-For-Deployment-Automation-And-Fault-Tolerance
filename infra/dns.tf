#===============================================================================
# Route 53 DNS Configuration
#===============================================================================

# Hosted Zone - survives terraform destroy
resource "aws_route53_zone" "main" {
  name = var.domain_name

  lifecycle {
    # prevent_destroy = true  # Won't be destroyed with terraform destroy
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
  zone_id = aws_route53_zone.main.zone_id
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
  zone_id         = aws_route53_zone.main.zone_id
}

# Wait for certificate validation to complete
resource "aws_acm_certificate_validation" "wildcard" {
  certificate_arn         = aws_acm_certificate.wildcard.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}
