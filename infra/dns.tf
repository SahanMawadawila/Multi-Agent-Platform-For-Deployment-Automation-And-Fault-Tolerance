#===============================================================================
# DNS Record — Points wildcard subdomain to ALB
# Route53 zone and ACM certificate are in infra/persistent/ (never destroyed)
#===============================================================================

# Wildcard DNS record — auto-updates when ALB changes
# Covers ALL subdomains: argocd.domain.com, app-42.domain.com, etc.
resource "aws_route53_record" "wildcard" {
  zone_id = var.route53_zone_id
  name    = "*"
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
