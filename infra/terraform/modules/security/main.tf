# ─────────────────────────────────────────────────────────────
# Security Module · Zero-Trust · Military-Grade
# ─────────────────────────────────────────────────────────────

variable "vault_addr" { type = string }

# ── Vault PKI for mTLS ───────────────────────────────────────

resource "vault_mount" "pki" {
  path                      = "pki"
  type                      = "pki"
  default_lease_ttl_seconds = 86400     # 1 day
  max_lease_ttl_seconds     = 31536000  # 1 year
}

resource "vault_pki_secret_backend_root_cert" "root" {
  backend     = vault_mount.pki.path
  type        = "internal"
  common_name = "Cortex Sovereign Root CA"
  ttl         = "87600h"
  key_bits    = 4096
}

resource "vault_pki_secret_backend_role" "service" {
  backend          = vault_mount.pki.path
  name             = "cortex-service"
  allowed_domains  = ["cortex-sovereign.internal"]
  allow_subdomains = true
  max_ttl          = "72h"
  key_bits         = 2048
  key_usage        = ["DigitalSignature", "KeyEncipherment"]
  require_cn       = true
}

# ── Vault KV for application secrets ────────────────────────

resource "vault_mount" "kv" {
  path = "cortex-secrets"
  type = "kv-v2"
}

resource "vault_kv_secret_v2" "db_credentials" {
  mount = vault_mount.kv.path
  name  = "database/cortex"

  data_json = jsonencode({
    username = "cortex_admin"
    password = "ROTATED_BY_VAULT"
    host     = "alloydb.cortex-sovereign.internal"
    port     = 5432
    database = "cortex_production"
  })
}

# ── RBAC Policies ────────────────────────────────────────────

resource "vault_policy" "cortex_app" {
  name = "cortex-application"

  policy = <<-EOT
    # Allow reading database credentials
    path "cortex-secrets/data/database/*" {
      capabilities = ["read"]
    }

    # Allow requesting TLS certificates
    path "pki/issue/cortex-service" {
      capabilities = ["create", "update"]
    }

    # Deny everything else
    path "*" {
      capabilities = ["deny"]
    }
  EOT
}

resource "vault_policy" "cortex_admin" {
  name = "cortex-admin"

  policy = <<-EOT
    # Full access to cortex secrets
    path "cortex-secrets/*" {
      capabilities = ["create", "read", "update", "delete", "list"]
    }

    # PKI management
    path "pki/*" {
      capabilities = ["create", "read", "update", "delete", "list"]
    }

    # Audit logs (read-only)
    path "sys/audit" {
      capabilities = ["read", "list"]
    }
  EOT
}

# ── Kubernetes Auth ──────────────────────────────────────────

resource "vault_auth_backend" "kubernetes" {
  type = "kubernetes"
}

resource "vault_kubernetes_auth_backend_role" "cortex" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "cortex-service"
  bound_service_account_names      = ["cortex-app"]
  bound_service_account_namespaces = ["cortex"]
  token_ttl                        = 3600
  token_policies                   = [vault_policy.cortex_app.name]
}

# ── Audit Logging ────────────────────────────────────────────

resource "vault_audit" "file" {
  type = "file"
  options = {
    file_path = "/vault/logs/audit.log"
    format    = "json"
  }
}

# ── Output ───────────────────────────────────────────────────

output "vault_status" {
  value = "configured"
}
