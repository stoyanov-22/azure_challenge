# Providers
terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.21.0"
    }
  }
}

# Create Azure Databricks Workspace
resource "azurerm_databricks_workspace" "this" {
  name                        = "${var.env_prefix}-dbr-demo-project-stoyan"
  location                    = var.location
  resource_group_name         = var.rg_name
  sku                         = "premium"
  managed_resource_group_name = "${var.env_prefix}-rg-demo-project-stoyan-db"
}

# Configure Databricks provider (MSI)
provider "databricks" {
  host          = azurerm_databricks_workspace.this.workspace_url
  azure_use_msi = true
}

# Create a PAT (token) for ADF
resource "databricks_token" "adf_token" {
  comment          = "Token for ADF Linked Service"
  lifetime_seconds = 2592000 # 30 days

  depends_on = [azurerm_databricks_workspace.this]
}

# Python Notebooks
resource "databricks_notebook" "my_python_notebook" {
  path     = "/Workspace/Shared/weather_api_notebook"
  language = "PYTHON"
  source   = "weather_api_notebook.py"

  depends_on = [azurerm_databricks_workspace.this]
}

resource "databricks_notebook" "configs_notebook" {
  path     = "/Workspace/Shared/utils"
  language = "PYTHON"
  source   = "utils.py"

  depends_on = [azurerm_databricks_workspace.this]
}

# Example Databricks Cluster
resource "databricks_cluster" "test_cluster" {
  cluster_name            = "${var.env_prefix}-test-cluster"
  spark_version           = "13.3.x-scala2.12"
  node_type_id            = "Standard_DS3_v2"
  autotermination_minutes = 10
  num_workers             = 1

  depends_on = [azurerm_databricks_workspace.this]
}

# Create a secret scope referencing Key Vault
resource "databricks_secret_scope" "example" {
  name         = "my-keyvault-scope"
  backend_type = "AZURE_KEYVAULT"

  keyvault_metadata {
    resource_id = var.key_vault_id
    dns_name    = var.key_vault_uri
  }

  depends_on = [azurerm_databricks_workspace.this]
}
