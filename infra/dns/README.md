# Central DNS Configuration

This folder contains Terraform configuration for the **shared DNS infrastructure**.

## Overview

- **Run once** by the DNS owner (person who controls the domain registrar)
- Creates the Route53 hosted zone for the root domain
- Manages subdomain delegations for teammates

## Workflow

### 1. DNS Owner (First-time Setup)

```bash
cd infra/dns
terraform init
terraform apply
```

After apply, update your domain registrar (Namecheap) with the outputted nameservers.

### 2. Adding Teammate Subdomains

When a teammate wants to use the platform:

1. **Teammate** creates a Route53 hosted zone for their subdomain in their AWS account:
   ```bash
   # In teammate's AWS account
   aws route53 create-hosted-zone --name "john.flowpilotai.me" --caller-reference $(date +%s)
   ```

2. **Teammate** sends you the 4 NS records from their zone

3. **DNS Owner** adds the delegation in `terraform.tfvars`:
   ```hcl
   delegated_subdomains = {
     "john.flowpilotai.me" = [
       "ns-123.awsdns-12.com",
       "ns-456.awsdns-34.net",
       "ns-789.awsdns-56.co.uk",
       "ns-101.awsdns-78.org"
     ]
     "jane.flowpilotai.me" = [
       # Jane's NS records...
     ]
   }
   ```

4. **DNS Owner** applies:
   ```bash
   terraform apply
   ```

5. **Teammate** can now run the main infra with their subdomain:
   ```bash
   cd ../  # back to infra/
   terraform apply -var="domain_name=john.flowpilotai.me" -var="is_dns_owner=false"
   ```

## Files

| File | Purpose |
|------|---------|
| `main.tf` | Route53 zone + NS delegation records |
| `variables.tf` | Configuration variables |
| `outputs.tf` | Nameservers and instructions |
| `terraform.tfvars` | Your delegated subdomains (create this) |

## Important Notes

- The hosted zone has `prevent_destroy = true` to avoid accidental deletion
- Nameservers only need to be set in the registrar ONCE
- Each teammate's subdomain is fully independent after delegation
