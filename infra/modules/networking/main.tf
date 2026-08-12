# AWS VPC Definition
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-vpc"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Internet Gateway for Public Subnets
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-igw"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Public Subnets
resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index % length(var.availability_zones)]
  map_public_ip_on_launch = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-public-subnet-${count.index + 1}"
      Type        = "Public"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Private Application Subnets
resource "aws_subnet" "private" {
  count                   = length(var.private_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index % length(var.availability_zones)]
  map_public_ip_on_launch = false

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-private-subnet-${count.index + 1}"
      Type        = "Private"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Database Subnets (Isolated)
resource "aws_subnet" "database" {
  count                   = length(var.database_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.database_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index % length(var.availability_zones)]
  map_public_ip_on_launch = false

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-db-subnet-${count.index + 1}"
      Type        = "Database"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# DB Subnet Group for RDS / ElastiCache
resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids  = aws_subnet.database[*].id
  description = "Database subnet group for ${var.project_name} ${var.environment}"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-db-subnet-group"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count  = var.enable_single_nat_gateway ? 1 : length(var.public_subnet_cidrs)
  domain = "vpc"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-nat-eip-${count.index + 1}"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [aws_internet_gateway.main]
}

# NAT Gateway(s) for Private Subnet Outbound Traffic
resource "aws_nat_gateway" "main" {
  count         = var.enable_single_nat_gateway ? 1 : length(var.public_subnet_cidrs)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-nat-gw-${count.index + 1}"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [aws_internet_gateway.main]
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-public-rt"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Private Route Table(s)
resource "aws_route_table" "private" {
  count  = var.enable_single_nat_gateway ? 1 : length(var.private_subnet_cidrs)
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[var.enable_single_nat_gateway ? 0 : count.index].id
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-private-rt-${count.index + 1}"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Database Route Table (No Internet Routing)
resource "aws_route_table" "database" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-db-rt"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(var.public_subnet_cidrs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnet_cidrs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[var.enable_single_nat_gateway ? 0 : count.index].id
}

resource "aws_route_table_association" "database" {
  count          = length(var.database_subnet_cidrs)
  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database.id
}
