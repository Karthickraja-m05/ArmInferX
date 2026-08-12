# IAM Assume Role Policy Document for EC2 / Graviton Nodes
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# IAM Role for AWS Graviton (ARM64) Instances
resource "aws_iam_role" "graviton_node_role" {
  name               = "${var.project_name}-${var.environment}-graviton-node-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-graviton-node-role"
      Architecture = "ARM64"
      Environment  = var.environment
      ManagedBy    = "Terraform"
    }
  )
}

# Attach AWS Managed SSM Instance Core Policy (for Systems Manager Session Manager access)
resource "aws_iam_role_policy_attachment" "ssm_managed" {
  role       = aws_iam_role.graviton_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach AWS Managed CloudWatch Agent Policy
resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.graviton_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Custom Policy for S3 Model Storage Access
data "aws_iam_policy_document" "s3_model_access" {
  statement {
    sid    = "S3ModelBucketReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:DeleteObject"
    ]
    resources = [
      var.s3_model_bucket_arn,
      "${var.s3_model_bucket_arn}/*"
    ]
  }
}

resource "aws_iam_policy" "s3_model_access" {
  name        = "${var.project_name}-${var.environment}-s3-model-access"
  description = "Allows Graviton nodes to access model artifacts in S3"
  policy      = data.aws_iam_policy_document.s3_model_access.json
}

resource "aws_iam_role_policy_attachment" "s3_model_access" {
  role       = aws_iam_role.graviton_node_role.name
  policy_arn = aws_iam_policy.s3_model_access.arn
}

# Custom Policy for Secrets Manager Read Access
data "aws_iam_policy_document" "secrets_access" {
  statement {
    sid    = "SecretsManagerRead"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [var.secrets_arn_prefix]
  }
}

resource "aws_iam_policy" "secrets_access" {
  name        = "${var.project_name}-${var.environment}-secrets-access"
  description = "Allows Graviton nodes to read database credentials and API secrets"
  policy      = data.aws_iam_policy_document.secrets_access.json
}

resource "aws_iam_role_policy_attachment" "secrets_access" {
  role       = aws_iam_role.graviton_node_role.name
  policy_arn = aws_iam_policy.secrets_access.arn
}

# Instance Profile for Launch Templates
resource "aws_iam_instance_profile" "graviton_profile" {
  name = "${var.project_name}-${var.environment}-graviton-profile"
  role = aws_iam_role.graviton_node_role.name

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-graviton-profile"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}
