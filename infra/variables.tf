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
  description = "Domain name for the platform (e.g., flowpilotai.me)"
  type        = string
  default     = "flowpilotai.me" # Change this to your domain
}

variable "route53_zone_id" {
  description = "Route53 Zone ID from the persistent stack (run: cd infra/persistent && terraform output zone_id)"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM Certificate ARN from the persistent stack (run: cd infra/persistent && terraform output acm_certificate_arn)"
  type        = string
}