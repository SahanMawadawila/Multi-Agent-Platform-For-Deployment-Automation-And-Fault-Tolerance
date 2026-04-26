#===============================================================================
# Monitoring Stack - Prometheus, Alertmanager, Grafana, and Blackbox Exporter
#===============================================================================

resource "helm_release" "kube_prometheus_stack" {
  name             = "prometheus"
  namespace        = "monitoring"
  create_namespace = true
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = "56.6.2"
  wait             = true

  values = [
    <<-EOT
    grafana:
      enabled: true

    prometheus:
      prometheusSpec:
        retention: 7d

    prometheus-blackbox-exporter:
      enabled: true
      config:
        modules:
          http_2xx:
            prober: http
            timeout: 5s
            http:
              valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
              valid_status_codes: []
              preferred_ip_protocol: "ip4"
          tcp_connect:
            prober: tcp
            timeout: 5s
    EOT
  ]

  depends_on = [
    module.eks
  ]
}