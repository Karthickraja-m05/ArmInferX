# Unique Random Suffix for S3 Bucket Naming
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# AWS KMS Customer Managed Key for S3 Encryption
resource "aws_kms_key" "model_storage" {
  description             = "KMS Key for encrypting ArmServe model storage bucket"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-kms-models"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

resource "aws_kms_alias" "model_storage" {
  name          = "alias/${var.project_name}-${var.environment}-models"
  target_key_id = aws_kms_key.model_storage.key_id
}

# S3 Bucket for AI Model Artifacts & Trial Checkpoints
resource "aws_s3_bucket" "models" {
  bucket        = "${var.project_name}-${var.environment}-models-${random_id.bucket_suffix.hex}"
  force_destroy = var.force_destroy

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-models"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Bucket Versioning
resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"
  }
}

# SSE-KMS Encryption Configuration
resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.model_storage.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Block All Public Access (Strict Security Enforcement)
resource "aws_s3_bucket_public_access_block" "models" {
  bucket = aws_s3_bucket.models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle Configuration (Transition old artifacts to Standard-IA and expire versions)
resource "aws_s3_bucket_lifecycle_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    id     = "model_retention_policy"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = var.expiration_days
    }
  }

  depends_on = [aws_s3_bucket_versioning.models]
}
