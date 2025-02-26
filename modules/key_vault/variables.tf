variable "env_prefix" {
  type = string
}
variable "location" {
  type = string
}
variable "tenant_id" {
  type = string
}
variable "rg_name" {
  type = string
}

variable "weather_api_key" {
  type = string
}

variable "object_id_for_access" {
  type = string
  description = "Object ID for Key Vault Access Policy (usually the Terraform SPN or user principal)."
}
