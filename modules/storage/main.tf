resource "random_string" "storage_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_storage_account" "storage" {
  name                     = "${var.env_prefix}dbstorage${random_string.storage_suffix.result}"
  resource_group_name      = var.rg_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_storage_container" "databricks_container" {
  name                  = "databricks"
  storage_account_id    = azurerm_storage_account.storage.id
  container_access_type = "private"
}

# Store the storage key in Key Vault
resource "azurerm_key_vault_secret" "storage_account_key" {
  name         = "storageAccountKey"
  value        = azurerm_storage_account.storage.primary_access_key
  key_vault_id = var.key_vault_id

  # Ensure Key Vault policy is set before storing secrets
  depends_on = [azurerm_storage_account.storage,
                var.key_vault_access_policy_id]
}

resource "azurerm_key_vault_secret" "storage_account_name" {
  name         = "storageAccountName"
  value        = azurerm_storage_account.storage.name
  key_vault_id = var.key_vault_id

  depends_on = [azurerm_storage_account.storage,
                var.key_vault_access_policy_id]
}
