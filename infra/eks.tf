#===============================================================================
# EKS Cluster Configuration
#===============================================================================

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.31.6"

  cluster_name    = var.cluster_name
  cluster_version = "1.32"

  # Cluster access
  cluster_endpoint_public_access = true

  # Add current caller as admin
  enable_cluster_creator_admin_permissions = true

  # Enable IRSA for service account IAM roles
  enable_irsa = true

  # Cluster addons - managed by AWS
  cluster_addons = {
    coredns = {
      most_recent = true
      configuration_values = jsonencode({
        tolerations = [
          {
            key      = "node.kubernetes.io/not-ready"
            operator = "Exists"
            effect   = "NoSchedule"
          }
        ]
      })
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent    = true
      before_compute = true # Ensure CNI is ready before nodes join
      configuration_values = jsonencode({
        env = {
          ENABLE_PREFIX_DELEGATION = "true"
          WARM_PREFIX_TARGET       = "1"
        }
      })
    }
  }

  # Networking
  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.intra_subnets

  # EKS Managed Node Group
  eks_managed_node_groups = {
    main = {
      name = "${var.cluster_name}-main"

      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = ["t3a.medium"]

      min_size     = 2
      max_size     = 4
      desired_size = 2

      # Labels for workload scheduling
      labels = {
        role = "general"
      }

      tags = {
        "Name" = "${var.cluster_name}-main-node"
      }
    }
  }

  tags = {
    Environment = "dev"
    Project     = var.cluster_name
  }
}
