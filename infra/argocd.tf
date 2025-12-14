#===============================================================================
# ArgoCD - GitOps Continuous Delivery
#===============================================================================

resource "helm_release" "argocd" {
  namespace        = "argocd"
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "5.51.6"
  create_namespace = true
  wait             = true

  values = [
    <<-EOT
    server:
      service:
        type: ClusterIP
      ingress:
        enabled: true
        ingressClassName: alb
        annotations:
          alb.ingress.kubernetes.io/scheme: internet-facing
          alb.ingress.kubernetes.io/target-type: ip
          alb.ingress.kubernetes.io/group.name: shared-alb
          alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}]'
          alb.ingress.kubernetes.io/healthcheck-path: /healthz
        hosts:
          - argocd.${var.domain_name}
    configs:
      params:
        server.insecure: true
    EOT
  ]

  depends_on = [
    helm_release.aws_load_balancer_controller
  ]
}

#===============================================================================
# ArgoCD Outputs
#===============================================================================

# Get the initial admin password
# Run: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
