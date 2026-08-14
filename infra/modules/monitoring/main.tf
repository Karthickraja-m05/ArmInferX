# CloudWatch Log Group for Backend API
resource "aws_cloudwatch_log_group" "backend_api" {
  name              = "/armserve/${var.environment}/backend"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name        = "/armserve/${var.environment}/backend"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# CloudWatch Log Group for Graviton ARM64 Benchmark Workers
resource "aws_cloudwatch_log_group" "graviton_worker" {
  name              = "/armserve/${var.environment}/graviton"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name         = "/armserve/${var.environment}/graviton"
      Architecture = "ARM64"
      Environment  = var.environment
      ManagedBy    = "Terraform"
    }
  )
}

# SNS Topic for System Alert Notifications
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-alerts"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Optional SNS Subscription if Email Provided
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != null ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Metric Alarm for Graviton ASG High CPU (>85%)
resource "aws_cloudwatch_metric_alarm" "graviton_high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-graviton-high-cpu"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Alarm when Graviton ARM64 node pool average CPU utilization exceeds 85%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    AutoScalingGroupName = var.autoscaling_group_name
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-high-cpu-alarm"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}
