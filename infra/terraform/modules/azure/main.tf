# ─────────────────────────────────────────────────────────────
# Azure Module · VNet + AKS + Cosmos DB + Key Vault
# ─────────────────────────────────────────────────────────────

variable "environment" { type = string }
variable "location" { type = string }

locals {
  name_prefix = "cortex-sovereign-${var.environment}"
  rg_name     = "${local.name_prefix}-rg"
}

# ── Resource Group ───────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = local.rg_name
  location = var.location
  tags     = { Standard = "130/100", ManagedBy = "terraform" }
}

# ── VNet ─────────────────────────────────────────────────────

resource "azurerm_virtual_network" "main" {
  name                = "${local.name_prefix}-vnet"
  address_space       = ["10.50.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_subnet" "aks" {
  name                 = "${local.name_prefix}-aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.50.1.0/24"]
}

# ── AKS ──────────────────────────────────────────────────────

resource "azurerm_kubernetes_cluster" "sovereign" {
  name                = "${local.name_prefix}-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = local.name_prefix
  sku_tier            = "Standard"

  default_node_pool {
    name           = "system"
    node_count     = 3
    vm_size        = "Standard_D4s_v5"
    vnet_subnet_id = azurerm_subnet.aks.id

    upgrade_settings {
      max_surge = "25%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "calico"
    load_balancer_sku = "standard"
  }

  azure_active_directory_role_based_access_control {
    azure_rbac_enabled = true
    managed            = true
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.sovereign.id
  }

  tags = { Standard = "130/100" }
}

# ── Log Analytics ────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "sovereign" {
  name                = "${local.name_prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 90
}

# ── Key Vault ────────────────────────────────────────────────

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "sovereign" {
  name                       = "cortexsov${var.environment}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "premium"
  purge_protection_enabled   = true
  soft_delete_retention_days = 90

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }
}

# ── Outputs ──────────────────────────────────────────────────

output "aks_endpoint" {
  value = azurerm_kubernetes_cluster.sovereign.fqdn
}

output "key_vault_uri" {
  value = azurerm_key_vault.sovereign.vault_uri
}
