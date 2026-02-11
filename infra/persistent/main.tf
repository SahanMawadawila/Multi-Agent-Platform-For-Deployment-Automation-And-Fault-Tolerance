#===============================================================================
# Persistent DNS Stack — Terraform Configuration
# This stack is applied ONCE and NEVER destroyed.
# It manages Route53 hosted zone and ACM certificate.
#===============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# AWS Provider
provider "aws" {
  region = var.region
}
