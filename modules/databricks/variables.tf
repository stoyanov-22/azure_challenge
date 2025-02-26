variable "env_prefix" {
  type = string
}
variable "location" {
  type = string
}
variable "rg_name" {
  type = string
}
variable "tenant_id" {
  type = string
}

variable "key_vault_id" {
  type        = string
  description = "Optional: If you need KV for your Databricks scope"
}

variable "key_vault_uri" {
  type        = string
  description = "Optional: If you need KV URI for Databricks scope"
}

variable "object_id_for_access" {
  type        = string
  description = "Object ID for assignment, if needed."
}
