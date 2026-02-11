# Persistent DNS Stack

This Terraform stack manages **Route53 hosted zone** and **ACM wildcard certificate** — resources that should **NEVER be destroyed**, even when you tear down EKS/ALB to save costs.

| Resource | Cost | Destroy? |
|---|---|---|
| Route53 Hosted Zone | $0.50/month | ❌ Never |
| ACM Certificate | FREE | ❌ Never |

---

## Setup Guide

### Person A (Domain Manager) — One-Time Setup

**1. Apply this stack:**
```bash
cd infra/persistent
terraform init
terraform apply
```

**2. Copy nameservers to Namecheap:**
```bash
terraform output nameservers
# Example output:
# [
#   "ns-111.awsdns-01.org",
#   "ns-222.awsdns-02.co.uk",
#   "ns-333.awsdns-03.com",
#   "ns-444.awsdns-04.net",
# ]
```

Go to **Namecheap Dashboard → Domain → Nameservers → Custom DNS** and paste all 4 nameservers.

> ⚠️ This is done ONCE. Never touch Namecheap again.

**3. Note the outputs for the main infra stack:**
```bash
terraform output zone_id
terraform output acm_certificate_arn
```

You'll use these when running `terraform apply` on the main `infra/` stack.

**4. (If using subdomain delegation) Add NS records for team members:**

If Person B runs their own persistent stack (e.g., for `janani.flowpilotai.me`), they'll give you their 4 nameservers. Add delegation records in the AWS Route53 Console:

```
Type: NS
Name: janani.flowpilotai.me
Value: [Person B's 4 nameservers]
```

---

### Person B/C — One-Time Setup (Subdomain Delegation)

> Only needed if using separate subdomains per person.

**1. Create `infra/persistent/terraform.tfvars`:**
```hcl
domain_name = "janani.flowpilotai.me"  # Your subdomain
```

**2. Apply this stack:**
```bash
cd infra/persistent
terraform init
terraform apply
```

**3. Give your nameservers to Person A:**
```bash
terraform output nameservers
# Send these 4 values to Person A
```

**4. Note your outputs:**
```bash
terraform output zone_id
terraform output acm_certificate_arn
```

---

## Every `terraform apply` on Main Infra Stack

When you apply the main `infra/` stack, you need to provide the persistent stack outputs.

**Create `infra/terraform.tfvars`** (one-time, gitignored):
```hcl
route53_zone_id     = "Z1234567890ABC"
acm_certificate_arn = "arn:aws:acm:ap-south-1:123456:certificate/abc-123"
```

Then simply:
```bash
cd infra
terraform apply
```

> 💡 The `terraform.tfvars` file is gitignored, so each person has their own values.

---

## Every `terraform destroy` on Main Infra Stack

```bash
cd infra
terraform destroy
```

This destroys EKS, ALB, VPC — but **Route53 zone and ACM certificate remain untouched** in the persistent stack. No action needed.

---

## DevOps Agents `.env` Setup

After applying the persistent stack, add these to your `devops_agents/.env`:
```bash
ACM_CERTIFICATE_ARN=arn:aws:acm:ap-south-1:123456:certificate/abc-123
DOMAIN_NAME=flowpilotai.me  # Or your subdomain like janani.flowpilotai.me
```
