output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "databricks_workspace_url" {
  value = azurerm_databricks_workspace.databricks.workspace_url
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}

output "storage_account_name" {
  value = azurerm_storage_account.storage.name
}

output "subscription_id" {
  value       = var.subscription_id
  description = "Azure Subscription ID"
}

output "tenant_id" {
  value       = var.tenant_id
  description = "Azure Tenant ID"
}

output "object_id" {
  value       = var.object_id
  description = "Azure Active Directory Object ID"
}

output "location" {
  value       = var.location
  description = "Azure Region"
}

output "env_prefix" {
  value       = var.env_prefix
  description = "Environment prefix"
}

output "databricks_token" {
  value       = databricks_token.adf_token.token_value
  description = "Databricks Personal Access Token for ADF Linked Service"
  sensitive   = true
}

output "weather_api_key" {
  value       = var.weather_api_key
  description = "API Key for Weather API"
  sensitive   = true
}