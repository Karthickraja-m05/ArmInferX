output "bucket_id" {
  description = "The ID/name of the S3 model storage bucket"
  value       = aws_s3_bucket.models.id
}

output "bucket_arn" {
  description = "The ARN of the S3 model storage bucket"
  value       = aws_s3_bucket.models.arn
}

output "bucket_domain_name" {
  description = "The regional domain name of the S3 bucket"
  value       = aws_s3_bucket.models.bucket_regional_domain_name
}

output "kms_key_arn" {
  description = "The ARN of the KMS key encrypting the storage bucket"
  value       = aws_kms_key.model_storage.arn
}

output "kms_key_alias" {
  description = "The alias name of the KMS key"
  value       = aws_kms_alias.model_storage.name
}
