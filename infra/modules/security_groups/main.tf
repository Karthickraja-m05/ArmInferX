# Application Load Balancer Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Security group for public facing Application Load Balancer"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-alb-sg"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

resource "aws_security_group_rule" "alb_http_ingress" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
  description       = "Allow HTTP inbound from anywhere"
}

resource "aws_security_group_rule" "alb_https_ingress" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
  description       = "Allow HTTPS inbound from anywhere"
}

resource "aws_security_group_rule" "alb_egress_backend" {
  type                     = "egress"
  from_port                = var.api_port
  to_port                  = var.api_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.backend_api.id
  security_group_id        = aws_security_group.alb.id
  description              = "Allow outbound to Backend API"
}

# Backend API Service Security Group
resource "aws_security_group" "backend_api" {
  name        = "${var.project_name}-${var.environment}-backend-api-sg"
  description = "Security group for backend API instances/containers"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-backend-api-sg"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

resource "aws_security_group_rule" "backend_ingress_alb" {
  type                     = "ingress"
  from_port                = var.api_port
  to_port                  = var.api_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.backend_api.id
  description              = "Allow inbound traffic from ALB only"
}

resource "aws_security_group_rule" "backend_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.backend_api.id
  description       = "Allow all outbound traffic for API backend"
}

# ARM64 Graviton Compute Nodes Security Group
resource "aws_security_group" "graviton_compute" {
  name        = "${var.project_name}-${var.environment}-graviton-compute-sg"
  description = "Security group for AWS Graviton (ARM64) worker/benchmark nodes"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name         = "${var.project_name}-${var.environment}-graviton-compute-sg"
      Architecture = "ARM64"
      Environment  = var.environment
      ManagedBy    = "Terraform"
    }
  )
}

resource "aws_security_group_rule" "graviton_ingress_backend" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.backend_api.id
  security_group_id        = aws_security_group.graviton_compute.id
  description              = "Allow internal traffic from backend API"
}

resource "aws_security_group_rule" "graviton_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.graviton_compute.id
  description       = "Allow all outbound traffic for package installs and model fetching"
}

# Database Security Group
resource "aws_security_group" "database" {
  name        = "${var.project_name}-${var.environment}-database-sg"
  description = "Security group for PostgreSQL database and Redis cache"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-database-sg"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

resource "aws_security_group_rule" "database_ingress_backend" {
  type                     = "ingress"
  from_port                = var.db_port
  to_port                  = var.db_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.backend_api.id
  security_group_id        = aws_security_group.database.id
  description              = "Allow PostgreSQL access from backend API"
}

resource "aws_security_group_rule" "database_ingress_graviton" {
  type                     = "ingress"
  from_port                = var.db_port
  to_port                  = var.db_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.graviton_compute.id
  security_group_id        = aws_security_group.database.id
  description              = "Allow PostgreSQL access from Graviton compute nodes"
}
