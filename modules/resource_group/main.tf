resource "azurerm_resource_group" "rg" {
  name     = "${var.env_prefix}-rg-demo-project-stoyan"
  location = var.location
}