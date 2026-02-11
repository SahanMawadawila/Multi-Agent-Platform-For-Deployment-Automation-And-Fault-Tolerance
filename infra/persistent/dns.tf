#===============================================================================
# Route 53 Hosted Zone (Persistent — NEVER destroy)
#===============================================================================

resource "aws_route53_zone" "main" {
  name = var.domain_name

  lifecycle {
    prevent_destroy = true # Safety: prevents accidental destruction
  }

  tags = {
    Environment = "dev"
    ManagedBy   = "persistent-stack"
  }
}

#===============================================================================
# ACM Certificate for HTTPS (Wildcard) — NEVER destroy
#===============================================================================

# Request wildcard certificate (covers *.flowpilotai.me + flowpilotai.me)
resource "aws_acm_certificate" "wildcard" {
  domain_name       = "*.${var.domain_name}"
  validation_method = "DNS"

  subject_alternative_names = [var.domain_name] # Also cover root domain

  lifecycle {
    create_before_destroy = true
    prevent_destroy       = true # Safety: prevents accidental destruction
  }

  tags = {
    Environment = "dev"
    ManagedBy   = "persistent-stack"
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
