data "azurerm_client_config" "current" {}

# Random suffix for Key Vault name
resource "random_string" "kv" {
  length  = 6
  special = false
  upper   = false
}

# Azure Key Vault
resource "azurerm_key_vault" "kv" {
  name                     = "${var.env_prefix}-kv-${random_string.kv.result}"
  location                 = var.location
  resource_group_name      = var.rg_name
  sku_name                 = "standard"
  tenant_id                = var.tenant_id
  purge_protection_enabled = false
}

# Give Terraform client access to Key Vault
resource "azurerm_key_vault_access_policy" "terraform" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get",
    "Set",
    "Delete",
    "List",
    "Purge"
  ]
}

# Weather API secret
resource "azurerm_key_vault_secret" "weather_secret" {
  name         = "weather-api"
  value        = var.weather_api_key
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [
    azurerm_key_vault_access_policy.terraform
  ]

  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "weather_logs_token" {
  name         = "weather-logs"
  value        = var.weather_logs_token
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [
    azurerm_key_vault_access_policy.terraform
  ]

  lifecycle {
    ignore_changes = [value]
  }
}