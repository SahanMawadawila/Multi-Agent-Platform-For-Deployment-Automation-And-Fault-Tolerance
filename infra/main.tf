#Infrastructure configuration wll be here
provider "aws" {
    region = var.region
}

terraform {
  required_version = ">= 0.13"

  required_providers { 
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = ">= 1.7.0"
    }
  }
}

#Helm provider to deploy helm charts to eks cluster
provider "helm" {
  kubernetes = {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec ={
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      # This requires the awscli to be installed locally where Terraform is executed
      args = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

provider "kubectl" {
  apply_retry_count      = 5
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  load_config_file       = false

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    # This requires the awscli to be installed locally where Terraform is executed
    args = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

data "aws_availability_zones" "available" {}


module "vpc" {
    source = "terraform-aws-modules/vpc/aws"
    version = "6.5.1"

    name                 = "${var.cluster_name}-vpc"
    cidr                 = var.vpc_cidr
    azs                  = data.aws_availability_zones.available.names
    public_subnets       = var.public_subnet_cidrs
    private_subnets      = var.private_subnet_cidrs
    intra_subnets           = var.intra_subnet_cidrs

    enable_dns_hostnames = true #aws will assign dns hostnames to ec2 instances. easy for integration
    enable_nat_gateway = true #private subnets can initiate outbound traffic to the internet via nat gateway (pull images)
    single_nat_gateway = true #one nat for whole vpc, all private subnets will use that to access internet, reduce cost and also availability in single failure zone

    tags = {
        "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    }

    public_subnet_tags = {
        "kubernetes.io/role/elb" = "1", #allow elb to be created in public subnet
        "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    }

    private_subnet_tags = {
        "kubernetes.io/role/internal-elb" = "1", #allow internal elb to be created in private subnet
        "kubernetes.io/cluster/${var.cluster_name}" = "shared"
        "karpenter.sh/discovery" = var.cluster_name  #allow karpenter to discover these subnets for provisioning
    }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.10.1"

  name               =  var.cluster_name
  kubernetes_version = "1.33"

  # Optional
  endpoint_public_access = true

  # Optional: Adds the current caller identity as an administrator via cluster access entry
  enable_cluster_creator_admin_permissions = true

  compute_config = {
    enabled    = true
    node_pools = ["general-purpose"]
  }

  vpc_id     = module.vpc.vpc_id
    subnet_ids = module.vpc.private_subnets
    control_plane_subnet_ids = module.vpc.intra_subnets #kubernates control plane will be in intra subnets, no internet access
    eks_managed_node_groups = {
            karpenter = {
            ami_type        = "AL2023_x86_64_STANDARD"
            instance_types  = ["t3a.medium", "t3a.large", "m5a.large", "m5a.xlarge"]

            min_size        = 0
            max_size        = 5
            desired_size    = 1

            taints = {
                addons = {
                    key    = "CriticalAddonsOnly"
                    value  = "true"
                    effect = "NO_SCHEDULE"
                }
            }
        }
    }

    node_security_group_tags = {
        "karpenter.sh/discovery" = var.cluster_name  #allow karpenter to discover these nodes for provisioning
    }
}

module "karpenter" {
  source = "terraform-aws-modules/eks/aws//modules/karpenter"

  cluster_name = module.eks.cluster_name

  create_pod_identity_association = true

  # Attach additional IAM policies to the Karpenter node IAM role
  node_iam_role_additional_policies = {
    AmazonSSMManagedInstanceCore = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  }
}

#karpenter helm release
resource "helm_release" "karpenter" {
  namespace           = "kube-system"
  name                = "karpenter"
  repository          = "oci://public.ecr.aws/karpenter"
  chart               = "karpenter"
  version             = "1.0.0"
  wait                = false

  values = [
    <<-EOT
    serviceAccount:
      name: ${module.karpenter.service_account}
    settings:
      clusterName: ${module.eks.cluster_name}
      clusterEndpoint: ${module.eks.cluster_endpoint}
      interruptionQueue: ${module.karpenter.queue_name}
    EOT
  ]
}

###############################################################################
# Karpenter Kubectl
###############################################################################
resource "kubectl_manifest" "karpenter_node_pool" {
  yaml_body = <<-YAML
    apiVersion: karpenter.sh/v1beta1
    kind: NodePool
    metadata:
      name: default
    spec:
      template:
        spec:
          nodeClassRef:
            name: default
          requirements:
            - key: "karpenter.k8s.aws/instance-category"
              operator: In
              values: ["c", "m", "r"]
            - key: "karpenter.k8s.aws/instance-cpu"
              operator: In
              values: ["4", "8", "16", "32"]
            - key: "karpenter.k8s.aws/instance-hypervisor"
              operator: In
              values: ["nitro"]
            - key: "karpenter.k8s.aws/instance-generation"
              operator: Gt
              values: ["2"]
      limits:
        cpu: 1000
      disruption:
        consolidationPolicy: WhenEmpty
        consolidateAfter: 30s
  YAML

  depends_on = [
    kubectl_manifest.karpenter_node_class
  ]
}

resource "kubectl_manifest" "karpenter_node_class" {
  yaml_body = <<-YAML
    apiVersion: karpenter.k8s.aws/v1beta1
    kind: EC2NodeClass
    metadata:
      name: default
    spec:
      amiFamily: AL2023
      role: ${module.karpenter.node_iam_role_name}
      subnetSelectorTerms:
        - tags:
            karpenter.sh/discovery: ${module.eks.cluster_name}
      securityGroupSelectorTerms:
        - tags:
            karpenter.sh/discovery: ${module.eks.cluster_name}
      tags:
        karpenter.sh/discovery: ${module.eks.cluster_name}
  YAML

  depends_on = [
    helm_release.karpenter
  ]
}
