output "id" {
  description = "Key Vault Resource ID"
  value       = azurerm_key_vault.kv.id
}

output "uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.kv.vault_uri
}

output "name" {
  description = "Key Vault Name"
  value       = azurerm_key_vault.kv.name
}

output "key_vault_access_policy_id" {
  value = azurerm_key_vault_access_policy.terraform.id
}