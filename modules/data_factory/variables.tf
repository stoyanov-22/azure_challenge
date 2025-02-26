variable "env_prefix" {
  type = string
}
variable "location" {
  type = string
}
variable "rg_name" {
  type = string
}

variable "databricks_workspace_url" {
  type = string
}

variable "databricks_token" {
  type      = string
  sensitive = true
}
