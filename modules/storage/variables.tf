variable "env_prefix" {
  type = string
}
variable "location" {
  type = string
}
variable "rg_name" {
  type = string
}
variable "key_vault_id" {
  type = string
}

variable "key_vault_access_policy_id" {
  type        = string
  description = "Key Vault Access Policy ID"
}