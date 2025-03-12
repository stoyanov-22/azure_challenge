variable "weather_api_key" {
  type        = string
  description = "API Key for Weather API"
}

variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID"
}

variable "tenant_id" {
  type        = string
  description = "Azure Tenant ID"
}

variable "location" {
  type        = string
  default     = "West Europe"
  description = "Azure Region"
}

variable "env_prefix" {
  type        = string
  default     = "dev"
  description = "Environment prefix to uniquely name resources"
}

variable "object_id" {
  type        = string
  description = "Azure Object ID"
}

variable "weather_logs_token" {
  type        = string
  description = "API Key for Weather API"
}