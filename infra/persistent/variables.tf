#===============================================================================
# Variables
#===============================================================================

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "domain_name" {
  description = "Domain name purchased from Namecheap (e.g., flowpilotai.me)"
  type        = string
  default     = "flowpilotai.me"
}
