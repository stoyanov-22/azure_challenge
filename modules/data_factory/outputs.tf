# Export the name of the Data Factory, pipeline name, etc. if needed
output "data_factory_name" {
  value = azurerm_data_factory.adf.name
}
