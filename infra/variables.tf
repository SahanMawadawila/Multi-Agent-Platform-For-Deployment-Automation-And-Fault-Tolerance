variable region {
    description = "AWS region to deploy resources in"
    type        = string
}

variable vpc_cidr {
    description = "CIDR block for the VPC"
    type        = string
}

variable public_subnet_cidrs {
    description = "List of CIDR blocks for public subnets"
    type        = list(string)
}

#private subnets can access internet via nat gateway
variable private_subnet_cidrs {
    description = "List of CIDR blocks for private subnets"
    type        = list(string)
}

variable intra_subnet_cidrs {
    description = "List of CIDR blocks for intra subnets. means no internet access"
    type        = list(string)
}

variable cluster_name {
    description = "Name of the Kubernetes cluster"
    type        = string
}