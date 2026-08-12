output "backend_log_group_name" {
  description = "CloudWatch log group name for backend API"
  value       = aws_cloudwatch_log_group.backend_api.name
}

output "graviton_log_group_name" {
  description = "CloudWatch log group name for Graviton workers"
  value       = aws_cloudwatch_log_group.graviton_worker.name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for monitoring alerts"
  value       = aws_sns_topic.alerts.arn
}

output "cpu_alarm_arn" {
  description = "ARN of the Graviton high CPU CloudWatch metric alarm"
  value       = aws_cloudwatch_metric_alarm.graviton_high_cpu.arn
}
