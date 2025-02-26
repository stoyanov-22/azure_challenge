output "workspace_url" {
  value = azurerm_databricks_workspace.this.workspace_url
}

output "token" {
  description = "Databricks token for ADF"
  value       = databricks_token.adf_token.token_value
  sensitive   = true
}
