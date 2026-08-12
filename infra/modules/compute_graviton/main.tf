# Dynamic Lookup for Official Canonical Ubuntu 22.04 LTS ARM64 AMI
data "aws_ami" "ubuntu_arm64" {
  most_recent = true
  owners      = ["099720109477"] # Canonical AWS Account ID

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

# Base User Data Script for Graviton ARM64 Initialization
locals {
  user_data_script = <<-EOF
    #!/bin/bash
    set -euo pipefail

    echo "=== Initializing ArmServe AWS Graviton (ARM64) Node ==="

    # Update system packages
    apt-get update -y
    apt-get upgrade -y
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        htop \
        numactl \
        sysstat \
        python3-pip \
        python3-venv

    # Install Docker CE for ARM64
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # Enable and start Docker service
    systemctl enable docker
    systemctl start docker

    # Custom extra user data initialization
    ${var.user_data_extra}

    echo "=== ArmServe Graviton (ARM64) Node Initialization Complete ==="
  EOF
}

# AWS Launch Template for Graviton Instances
resource "aws_launch_template" "graviton" {
  name_prefix   = "${var.project_name}-${var.environment}-graviton-"
  image_id      = data.aws_ami.ubuntu_arm64.id
  instance_type = var.instance_type

  iam_instance_profile {
    name = var.instance_profile_name
  }

  network_interfaces {
    associate_public_ip_address = false
    security_groups             = var.security_group_ids
  }

  block_device_mappings {
    device_name = "/dev/sda1"

    ebs {
      volume_size           = var.root_volume_size
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
      iops                  = 3000
      throughput            = 125
    }
  }

  user_data = base64encode(local.user_data_script)

  monitoring {
    enabled = true
  }

  tag_specifications {
    resource_type = "instance"

    tags = merge(
      var.tags,
      {
        Name         = "${var.project_name}-${var.environment}-graviton-node"
        Architecture = "ARM64"
        Environment  = var.environment
        ManagedBy    = "Terraform"
      }
    )
  }

  tag_specifications {
    resource_type = "volume"

    tags = merge(
      var.tags,
      {
        Name        = "${var.project_name}-${var.environment}-graviton-ebs"
        Environment = var.environment
        ManagedBy   = "Terraform"
      }
    )
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Group across Private Subnets
resource "aws_autoscaling_group" "graviton" {
  name_prefix         = "${var.project_name}-${var.environment}-graviton-asg-"
  vpc_zone_identifier = var.subnet_ids
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.desired_capacity

  launch_template {
    id      = aws_launch_template.graviton.id
    version = "$Latest"
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300
  force_delete              = false

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [desired_capacity]
  }

  dynamic "tag" {
    for_each = merge(
      var.tags,
      {
        Name         = "${var.project_name}-${var.environment}-asg-graviton-node"
        Architecture = "ARM64"
        Environment  = var.environment
        ManagedBy    = "Terraform"
      }
    )

    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}

# Target Tracking Scaling Policy based on Average CPU Utilization
resource "aws_autoscaling_policy" "cpu_scaling" {
  name                   = "${var.project_name}-${var.environment}-graviton-cpu-scaling"
  autoscaling_group_name = aws_autoscaling_group.graviton.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }

    target_value = 70.0
  }
}
