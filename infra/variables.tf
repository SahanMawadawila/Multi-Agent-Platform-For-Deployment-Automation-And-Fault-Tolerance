#===============================================================================
# Variables
#===============================================================================

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "Flow-Pilot-AI"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

variable "intra_subnet_cidrs" {
  description = "CIDR blocks for intra subnets (EKS control plane)"
  type        = list(string)
  default     = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
}

variable "domain_name" {
  description = "Domain name for the platform (e.g., flowpilot.dev or john.flowpilot.dev for teammates)"
  type        = string
  default     = "flowpilotai.me"  # Change this to your domain or subdomain
}

#===============================================================================
# DNS Configuration Options
#===============================================================================

variable "is_dns_owner" {
  description = <<-EOT
    Set to true if you own the root domain and manage the central DNS.
    Set to false if you're a teammate using a delegated subdomain.
    
    - true:  Creates Route53 zone (for DNS owner only - use infra/dns instead)
    - false: Expects you to have your own Route53 zone for your subdomain
  EOT
  type        = bool
  default     = false  # Default to teammate mode (safer)
}

variable "external_zone_id" {
  description = <<-EOT
    Route53 Zone ID for your domain/subdomain.
    Required when is_dns_owner = false.
    Get this from your own Route53 hosted zone in your AWS account.
  EOT
  type        = string
  default     = ""
}