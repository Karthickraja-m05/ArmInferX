output "graviton_role_arn" {
  description = "ARN of the Graviton node IAM role"
  value       = aws_iam_role.graviton_node_role.arn
}

output "graviton_role_name" {
  description = "Name of the Graviton node IAM role"
  value       = aws_iam_role.graviton_node_role.name
}

output "graviton_instance_profile_name" {
  description = "Name of the IAM Instance Profile for Graviton EC2 instances"
  value       = aws_iam_instance_profile.graviton_profile.name
}

output "graviton_instance_profile_arn" {
  description = "ARN of the IAM Instance Profile for Graviton EC2 instances"
  value       = aws_iam_instance_profile.graviton_profile.arn
}
