# ─────────────────────────────────────────────────────────────
# Observability Module · OpenTelemetry + Prometheus + Grafana
# ─────────────────────────────────────────────────────────────

variable "environment" { type = string }

# ── Helm releases for the observability stack ────────────────

resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = "observability"
  version    = "57.0.0"

  create_namespace = true

  values = [
    yamlencode({
      grafana = {
        adminPassword = "CHANGE_ME"
        ingress = {
          enabled = true
          hosts   = ["grafana.cortex-sovereign.internal"]
        }
        dashboardProviders = {
          dashboardproviders_yaml = {
            apiVersion = 1
            providers = [{
              name      = "sovereign"
              folder    = "Sovereign"
              type      = "file"
              options   = { path = "/var/lib/grafana/dashboards/sovereign" }
            }]
          }
        }
      }

      prometheus = {
        prometheusSpec = {
          retention         = "30d"
          retentionSize     = "50GB"
          storageSpec = {
            volumeClaimTemplate = {
              spec = {
                accessModes = ["ReadWriteOnce"]
                resources   = { requests = { storage = "100Gi" } }
              }
            }
          }
          additionalScrapeConfigs = [
            {
              job_name        = "cortex-sovereign"
              scrape_interval = "15s"
              static_configs  = [{ targets = ["cortex-api.cortex.svc:8000"] }]
            },
            {
              job_name        = "otel-collector"
              scrape_interval = "15s"
              static_configs  = [{ targets = ["otel-collector.observability.svc:8888"] }]
            }
          ]
        }
      }

      alertmanager = {
        config = {
          global = { resolve_timeout = "5m" }
          route = {
            receiver = "sovereign-alerts"
            group_by = ["alertname", "namespace"]
            routes = [
              { match = { severity = "critical" }, receiver = "sovereign-critical" }
            ]
          }
          receivers = [
            { name = "sovereign-alerts" },
            {
              name = "sovereign-critical"
              webhook_configs = [{ url = "https://hooks.cortex-sovereign.internal/alerts" }]
            }
          ]
        }
      }
    })
  ]
}

resource "helm_release" "otel_collector" {
  name       = "otel-collector"
  repository = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart      = "opentelemetry-collector"
  namespace  = "observability"
  version    = "0.85.0"

  values = [
    yamlencode({
      mode = "deployment"
      config = {
        receivers = {
          otlp = {
            protocols = {
              grpc = { endpoint = "0.0.0.0:4317" }
              http = { endpoint = "0.0.0.0:4318" }
            }
          }
        }
        processors = {
          batch = { timeout = "5s", send_batch_size = 1024 }
          memory_limiter = {
            check_interval  = "1s"
            limit_mib       = 512
            spike_limit_mib = 128
          }
        }
        exporters = {
          prometheusremotewrite = {
            endpoint = "http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write"
          }
          otlp = {
            endpoint = "tempo.observability.svc:4317"
            tls      = { insecure = true }
          }
          loki = {
            endpoint = "http://loki.observability.svc:3100/loki/api/v1/push"
          }
        }
        service = {
          pipelines = {
            traces  = { receivers = ["otlp"], processors = ["memory_limiter", "batch"], exporters = ["otlp"] }
            metrics = { receivers = ["otlp"], processors = ["memory_limiter", "batch"], exporters = ["prometheusremotewrite"] }
            logs    = { receivers = ["otlp"], processors = ["memory_limiter", "batch"], exporters = ["loki"] }
          }
        }
      }
    })
  ]
}

resource "helm_release" "loki" {
  name       = "loki"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  namespace  = "observability"
  version    = "5.47.0"

  values = [
    yamlencode({
      loki = {
        auth_enabled = false
        storage = { type = "filesystem" }
      }
      singleBinary = { replicas = 1, persistence = { size = "50Gi" } }
    })
  ]
}

resource "helm_release" "tempo" {
  name       = "tempo"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "tempo"
  namespace  = "observability"
  version    = "1.7.0"
}
