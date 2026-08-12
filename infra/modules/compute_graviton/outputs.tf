output "launch_template_id" {
  description = "ID of the Graviton launch template"
  value       = aws_launch_template.graviton.id
}

output "launch_template_arn" {
  description = "ARN of the Graviton launch template"
  value       = aws_launch_template.graviton.arn
}

output "autoscaling_group_id" {
  description = "ID of the Graviton Auto Scaling Group"
  value       = aws_autoscaling_group.graviton.id
}

output "autoscaling_group_name" {
  description = "Name of the Graviton Auto Scaling Group"
  value       = aws_autoscaling_group.graviton.name
}

output "autoscaling_group_arn" {
  description = "ARN of the Graviton Auto Scaling Group"
  value       = aws_autoscaling_group.graviton.arn
}

output "ami_id" {
  description = "AMI ID used for ARM64 Graviton instances"
  value       = data.aws_ami.ubuntu_arm64.id
}
