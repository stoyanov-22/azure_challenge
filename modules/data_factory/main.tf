# Azure Data Factory
resource "azurerm_data_factory" "adf" {
  name                = "${var.env_prefix}-adf-demo-project-stoyan"
  location            = var.location
  resource_group_name = var.rg_name
}

# Linked Service to Databricks using token
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

  access_token = var.databricks_token
  adb_domain   = "https://${var.databricks_workspace_url}"

  depends_on = [
    azurerm_data_factory.adf
  ]
}

# ADF pipeline calling a Databricks Python Notebook
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

  depends_on = [
    azurerm_data_factory_linked_service_azure_databricks.at_linked
  ]
}

# ADF schedule trigger
resource "azurerm_data_factory_trigger_schedule" "daily_trigger" {
  name            = "DailyTrigger"
  data_factory_id = azurerm_data_factory.adf.id
  pipeline_name   = azurerm_data_factory_pipeline.databricks_pipeline.name

  frequency = "Day"
  interval  = 1

  schedule {
    hours   = [11]
    minutes = [0]
  }

  depends_on = [
    azurerm_data_factory_pipeline.databricks_pipeline
  ]
}
