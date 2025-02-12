# Terraform Configuration

terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.17.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.21.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0"
    }
  }
}

# AzureRM Provider

data "azurerm_client_config" "current" {}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}

# Resource Group

resource "azurerm_resource_group" "rg" {
  name     = "${var.env_prefix}-rg-demo-project-stoyan"
  location = var.location
}

# Databricks Workspace

resource "azurerm_databricks_workspace" "databricks" {
  name                        = "${var.env_prefix}-dbr-demo-project-stoyan"
  location                    = var.location
  resource_group_name         = azurerm_resource_group.rg.name
  sku                         = "premium"
  managed_resource_group_name = "${var.env_prefix}-rg-demo-project-stoyan-db"
}

provider "databricks" {
  host          = azurerm_databricks_workspace.databricks.workspace_url
  azure_use_msi = true
}

resource "databricks_token" "adf_token" {
  comment          = "Token for ADF Linked Service"
  lifetime_seconds = 2592000 # 30 days

  depends_on = [azurerm_databricks_workspace.databricks]
}

# Key Vault and Secrets

# Random suffix for unique Key Vault name
resource "random_string" "kv" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_key_vault" "kv" {
  name                     = "${var.env_prefix}-kv-${random_string.kv.result}"
  location                 = azurerm_resource_group.rg.location
  resource_group_name      = azurerm_resource_group.rg.name
  sku_name                 = "standard"
  tenant_id                = var.tenant_id
  purge_protection_enabled = false
}

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

# Notebooks in Databricks

resource "databricks_notebook" "my_python_notebook" {
  path     = "/Workspace/Shared/weather_api_notebook"
  language = "PYTHON"
  source   = "demo_notebook.py"

  depends_on = [azurerm_databricks_workspace.databricks]
}

# Storage (ADLS Gen2)

resource "azurerm_storage_account" "storage" {
  name                     = "${var.env_prefix}dbstorage${random_string.kv.result}"
  resource_group_name      = azurerm_resource_group.rg.name
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

# Store Storage Keys in Key Vault

resource "azurerm_key_vault_secret" "storage_account_key" {
  name         = "storageAccountKey"
  value        = azurerm_storage_account.storage.primary_access_key
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [
    azurerm_key_vault_access_policy.terraform
  ]
}

resource "azurerm_key_vault_secret" "storage_account_name" {
  name         = "storageAccountName"
  value        = azurerm_storage_account.storage.name
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [
    azurerm_key_vault_access_policy.terraform
  ]
}

# Databricks Secret Scope (linked to Key Vault)

resource "databricks_secret_scope" "example" {
  name         = "my-keyvault-scope"
  backend_type = "AZURE_KEYVAULT"

  keyvault_metadata {
    resource_id = azurerm_key_vault.kv.id
    dns_name    = azurerm_key_vault.kv.vault_uri
  }

  depends_on = [azurerm_databricks_workspace.databricks]
}

# Databricks Cluster Configuration

resource "databricks_cluster" "test_cluster" {
  cluster_name            = "${var.env_prefix}-test-cluster"
  spark_version           = "13.3.x-scala2.12"
  node_type_id            = "Standard_DS3_v2"
  autotermination_minutes = 10
  num_workers             = 1

  depends_on = [azurerm_databricks_workspace.databricks]
}

# Azure Data Factory

resource "azurerm_data_factory" "adf" {
  name                = "${var.env_prefix}-adf-demo-project-stoyan"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_data_factory_linked_service_azure_databricks" "at_linked" {
  name            = "ADBLinkedServiceViaAccessToken"
  data_factory_id = azurerm_data_factory.adf.id
  description     = "ADB Linked Service via Access Token"
  new_cluster_config {
    node_type             = "Standard_D4ds_v5"
    cluster_version       = "15.4.x-scala2.12"
    min_number_of_workers = 1
    max_number_of_workers = 2
    driver_node_type      = "Standard_D4ds_v5"
    log_destination       = "dbfs:/logs"
  }
  access_token = databricks_token.adf_token.token_value
  adb_domain   = "https://${azurerm_databricks_workspace.databricks.workspace_url}"

  depends_on = [
    azurerm_databricks_workspace.databricks,
    databricks_token.adf_token
  ]
}

# ADF pipeline that calls a Databricks Python Notebook

resource "azurerm_data_factory_pipeline" "databricks_pipeline" {
  name            = "RunPythonNotebookPipeline"
  data_factory_id = azurerm_data_factory.adf.id
  description     = "Pipeline that executes a Python notebook on Databricks"

  activities_json = <<JSON
[
  {
    "name": "RunPythonNotebook",
    "type": "DatabricksNotebook",
    "linkedServiceName": {
      "referenceName": "${azurerm_data_factory_linked_service_azure_databricks.at_linked.name}",
      "type": "LinkedServiceReference"
    },
    "typeProperties": {
      "notebookPath": "/Shared/weather_api_notebook",
      "baseParameters": {}
    },
    "policy": {
      "timeout": "7.00:00:00",
      "retry": 0,
      "retryIntervalInSeconds": 30,
      "secureOutput": false,
      "secureInput": false
    }
  }
]
JSON
  depends_on      = [azurerm_data_factory_linked_service_azure_databricks.at_linked]
}

# ADF Schedule Trigger - Runs the pipeline daily at 11:00 AM UTC
resource "azurerm_data_factory_trigger_schedule" "daily_trigger" {
  name            = "DailyTrigger"
  data_factory_id = azurerm_data_factory.adf.id
  pipeline_name   = azurerm_data_factory_pipeline.databricks_pipeline.name

  frequency = "Day"
  interval  = 1

  schedule {
    hours   = [11]
    minutes = [00]
  }

  depends_on = [
    azurerm_data_factory_pipeline.databricks_pipeline
  ]
}


