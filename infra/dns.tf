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
