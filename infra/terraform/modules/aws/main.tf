# ─────────────────────────────────────────────────────────────
# AWS Module · VPC + EKS + RDS · Zero-Trust Perimeter
# ─────────────────────────────────────────────────────────────

variable "environment" { type = string }
variable "region" { type = string }

locals {
  name_prefix = "cortex-sovereign-${var.environment}"
  azs         = ["${var.region}a", "${var.region}b", "${var.region}c"]
}

# ── VPC ──────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "${local.name_prefix}-vpc" }
}

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = local.azs[count.index]

  tags = { Name = "${local.name_prefix}-private-${count.index}" }
}

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 101}.0/24"
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "${local.name_prefix}-public-${count.index}" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-igw" }
}

# ── Security Groups (Military-Grade) ────────────────────────

resource "aws_security_group" "eks_nodes" {
  name_prefix = "${local.name_prefix}-eks-nodes-"
  vpc_id      = aws_vpc.main.id
  description = "EKS worker nodes — mTLS only"

  ingress {
    description = "Inter-node mTLS"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-eks-sg" }
}

resource "aws_security_group" "rds" {
  name_prefix = "${local.name_prefix}-rds-"
  vpc_id      = aws_vpc.main.id
  description = "RDS — only from EKS nodes"

  ingress {
    description     = "PostgreSQL from EKS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  tags = { Name = "${local.name_prefix}-rds-sg" }
}

# ── EKS Cluster ─────────────────────────────────────────────

resource "aws_iam_role" "eks_cluster" {
  name = "${local.name_prefix}-eks-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_eks_cluster" "sovereign" {
  name     = "${local.name_prefix}-eks"
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
    endpoint_public_access  = false
    security_group_ids      = [aws_security_group.eks_nodes.id]
  }

  encryption_config {
    provider { key_arn = aws_kms_key.eks.arn }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = { Name = "${local.name_prefix}-eks" }
}

resource "aws_kms_key" "eks" {
  description             = "EKS secrets encryption — AES-256"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = { Name = "${local.name_prefix}-eks-kms" }
}

# ── RDS PostgreSQL (encrypted, Multi-AZ) ────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "cortex" {
  identifier     = "${local.name_prefix}-pg"
  engine         = "postgres"
  engine_version = "16.2"
  instance_class = "db.r6g.xlarge"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = true

  backup_retention_period = 35
  deletion_protection     = true
  skip_final_snapshot     = false

  performance_insights_enabled = true

  tags = { Name = "${local.name_prefix}-rds" }
}

resource "aws_kms_key" "rds" {
  description             = "RDS encryption — AES-256"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

# ── Outputs ──────────────────────────────────────────────────

output "eks_endpoint" {
  value = aws_eks_cluster.sovereign.endpoint
}

output "vpc_id" {
  value = aws_vpc.main.id
}
