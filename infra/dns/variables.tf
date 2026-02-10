#===============================================================================
# Variables for Central DNS Configuration
#===============================================================================

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "domain_name" {
  description = "Root domain name (e.g., flowpilotai.me)"
  type        = string
  default     = "flowpilotai.me"
}

variable "delegated_subdomains" {
  description = <<-EOT
    Map of subdomain => list of nameservers for delegation.
    Each teammate creates their own Route53 hosted zone for their subdomain
    and provides the NS records here.
    
    Example:
    {
      "john.flowpilotai.me" = [
        "ns-123.awsdns-12.com",
        "ns-456.awsdns-34.net",
        "ns-789.awsdns-56.co.uk",
        "ns-101.awsdns-78.org"
      ]
    }
  EOT
  type        = map(list(string))
  default     = {}
}
