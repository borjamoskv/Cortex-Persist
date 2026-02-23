# ─────────────────────────────────────────────────────────────
# SOVEREIGN MULTI-CLOUD · Terraform Root Module
# Target: 1300/1000 power · Zero-Trust · HA across 3 clouds
# ─────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.95"
    }
    vault = {
      source  = "hashicorp/vault"
      version = "~> 4.2"
    }
  }

  backend "gcs" {
    bucket = "cortex-sovereign-tfstate"
    prefix = "sovereign/state"
  }
}

# ── Variables ────────────────────────────────────────────────

variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "cortex-sovereign"
}

variable "aws_region" {
  description = "Primary AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "gcp_region" {
  description = "Primary GCP region"
  type        = string
  default     = "europe-west1"
}

variable "azure_location" {
  description = "Primary Azure location"
  type        = string
  default     = "West Europe"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Must be production, staging, or development."
  }
}

variable "vault_addr" {
  description = "HashiCorp Vault address"
  type        = string
  default     = "https://vault.cortex-sovereign.internal:8200"
}

# ── Providers ────────────────────────────────────────────────

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "cortex-sovereign"
      Environment = var.environment
      ManagedBy   = "terraform"
      Standard    = "130/100"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.gcp_region
}

provider "azurerm" {
  features {}
}

provider "vault" {
  address = var.vault_addr
}

# ── Modules ──────────────────────────────────────────────────

module "aws_infra" {
  source      = "./modules/aws"
  environment = var.environment
  region      = var.aws_region
}

module "gcp_infra" {
  source      = "./modules/gcp"
  environment = var.environment
  project_id  = var.project_id
  region      = var.gcp_region
}

module "azure_infra" {
  source      = "./modules/azure"
  environment = var.environment
  location    = var.azure_location
}

module "security" {
  source     = "./modules/security"
  vault_addr = var.vault_addr
}

module "observability" {
  source      = "./modules/observability"
  environment = var.environment
  depends_on  = [module.aws_infra, module.gcp_infra, module.azure_infra]
}

# ── Outputs ──────────────────────────────────────────────────

output "aws_eks_endpoint" {
  value       = module.aws_infra.eks_endpoint
  description = "AWS EKS cluster endpoint"
}

output "gcp_gke_endpoint" {
  value       = module.gcp_infra.gke_endpoint
  description = "GCP GKE cluster endpoint"
}

output "azure_aks_endpoint" {
  value       = module.azure_infra.aks_endpoint
  description = "Azure AKS cluster endpoint"
}

output "vault_status" {
  value       = module.security.vault_status
  description = "Vault seal status"
}
