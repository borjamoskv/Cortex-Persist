# ─────────────────────────────────────────────────────────────
# GCP Module · VPC + GKE + AlloyDB + Cloud Armor
# ─────────────────────────────────────────────────────────────

variable "environment" { type = string }
variable "project_id" { type = string }
variable "region" { type = string }

locals {
  name_prefix = "cortex-sovereign-${var.environment}"
}

# ── VPC ──────────────────────────────────────────────────────

resource "google_compute_network" "main" {
  name                    = "${local.name_prefix}-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id
}

resource "google_compute_subnetwork" "private" {
  name          = "${local.name_prefix}-private"
  ip_cidr_range = "10.10.0.0/20"
  region        = var.region
  network       = google_compute_network.main.id
  project       = var.project_id

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.20.0.0/16"
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.30.0.0/20"
  }
}

# ── Cloud NAT ────────────────────────────────────────────────

resource "google_compute_router" "nat_router" {
  name    = "${local.name_prefix}-router"
  region  = var.region
  network = google_compute_network.main.id
  project = var.project_id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${local.name_prefix}-nat"
  router                             = google_compute_router.nat_router.name
  region                             = var.region
  project                            = var.project_id
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# ── GKE Autopilot ───────────────────────────────────────────

resource "google_container_cluster" "sovereign" {
  name     = "${local.name_prefix}-gke"
  location = var.region
  project  = var.project_id

  enable_autopilot = true

  network    = google_compute_network.main.id
  subnetwork = google_compute_subnetwork.private.id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "All (restrict in prod)"
    }
  }

  release_channel {
    channel = "REGULAR"
  }

  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  database_encryption {
    state    = "ENCRYPTED"
    key_name = google_kms_crypto_key.gke.id
  }
}

# ── KMS for GKE secrets ─────────────────────────────────────

resource "google_kms_key_ring" "sovereign" {
  name     = "${local.name_prefix}-keyring"
  location = var.region
  project  = var.project_id
}

resource "google_kms_crypto_key" "gke" {
  name     = "${local.name_prefix}-gke-key"
  key_ring = google_kms_key_ring.sovereign.id

  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

# ── AlloyDB (CORTEX primary database) ───────────────────────

resource "google_alloydb_cluster" "cortex" {
  cluster_id = "${local.name_prefix}-alloydb"
  location   = var.region
  project    = var.project_id

  network_config {
    network = google_compute_network.main.id
  }

  initial_user {
    user     = "cortex_admin"
    password = "CHANGE_ME_VIA_VAULT" # rotated by Vault
  }

  automated_backup_policy {
    enabled = true
    weekly_schedule {
      days_of_week = ["MONDAY", "WEDNESDAY", "FRIDAY"]
      start_times { hours = 2 }
    }
    backup_window   = "3600s"
    quantity_based_retention { count = 14 }
  }

  encryption_config {
    kms_key_name = google_kms_crypto_key.gke.id
  }
}

resource "google_alloydb_instance" "primary" {
  cluster       = google_alloydb_cluster.cortex.name
  instance_id   = "${local.name_prefix}-primary"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = 8
  }
}

# ── Cloud Armor (WAF) ───────────────────────────────────────

resource "google_compute_security_policy" "sovereign_waf" {
  name    = "${local.name_prefix}-waf"
  project = var.project_id

  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr { expression = "evaluatePreconfiguredExpr('sqli-v33-stable')" }
    }
    description = "Block SQL injection"
  }

  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr { expression = "evaluatePreconfiguredExpr('xss-v33-stable')" }
    }
    description = "Block XSS"
  }

  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
    description = "Default allow"
  }
}

# ── Outputs ──────────────────────────────────────────────────

output "gke_endpoint" {
  value = google_container_cluster.sovereign.endpoint
}

output "alloydb_ip" {
  value = google_alloydb_instance.primary.ip_address
}
