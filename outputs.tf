output "resource_group_name" {
  value = module.resource_group.name
}

output "databricks_workspace_url" {
  value = module.databricks.workspace_url
}

output "key_vault_name" {
  value = module.key_vault.name
}

output "key_vault_uri" {
  value = module.key_vault.uri
}

output "storage_account_name" {
  value = module.storage.storage_account_name
}

output "databricks_token" {
  value       = module.databricks.token
  description = "Databricks Personal Access Token"
  sensitive   = true
}
