# Top-level providers and data sources
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

provider "azurerm" {
  features       {}
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}

data "azurerm_client_config" "current" {}

# 1) Resource Group
module "resource_group" {
  source        = "./modules/resource_group"
  env_prefix    = var.env_prefix
  location      = var.location
}

# 2) Key Vault
module "key_vault" {
  source               = "./modules/key_vault"
  env_prefix           = var.env_prefix
  location             = var.location
  tenant_id            = var.tenant_id
  rg_name              = module.resource_group.name
  weather_api_key      = var.weather_api_key
  object_id_for_access = data.azurerm_client_config.current.object_id
  weather_logs_token   = var.weather_logs_token
}

# 3) Databricks Workspace & related resources
module "databricks" {
  source                    = "./modules/databricks"
  env_prefix                = var.env_prefix
  location                  = var.location
  rg_name                   = module.resource_group.name
  tenant_id                 = var.tenant_id
  key_vault_id             = module.key_vault.id
  key_vault_uri            = module.key_vault.uri
  object_id_for_access     = data.azurerm_client_config.current.object_id
}

# 4) Storage
module "storage" {
  source       = "./modules/storage"
  env_prefix   = var.env_prefix
  location     = var.location
  rg_name      = module.resource_group.name
  key_vault_id = module.key_vault.id
  key_vault_access_policy_id = module.key_vault.key_vault_access_policy_id
}

# 5) Data Factory
module "data_factory" {
  source                = "./modules/data_factory"
  env_prefix            = var.env_prefix
  location              = var.location
  rg_name               = module.resource_group.name
  databricks_workspace_url = module.databricks.workspace_url
  databricks_token      = module.databricks.token
}