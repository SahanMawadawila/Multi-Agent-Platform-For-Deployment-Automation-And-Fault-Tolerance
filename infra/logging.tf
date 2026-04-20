#===============================================================================
# Logging Aggregation - Loki and Promtail
#===============================================================================

resource "helm_release" "loki_stack" {
  namespace        = "logging"
  name             = "loki"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "loki-stack"
  create_namespace = true
  wait             = true

  values = [
    <<-EOT
    loki:
      enabled: true
      persistence:
        enabled: false
    promtail:
      enabled: true
    grafana:
      enabled: false
    EOT
  ]
}
