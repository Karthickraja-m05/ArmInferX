output "vpc_id" {
  description = "The ID of the AWS VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "The primary CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "List of IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of IDs of the private application subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "List of IDs of the isolated database subnets"
  value       = aws_subnet.database[*].id
}

output "database_subnet_group_name" {
  description = "Name of the RDS database subnet group"
  value       = aws_db_subnet_group.main.name
}

output "nat_gateway_ips" {
  description = "List of Elastic IP addresses assigned to NAT Gateways"
  value       = aws_eip.nat[*].public_ip
}
