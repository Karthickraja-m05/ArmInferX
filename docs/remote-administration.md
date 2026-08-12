# ArmServe Secure Remote Administration Specification & Connection Guide

This document defines the hardened SSH configuration, AWS Systems Manager (SSM) Session Manager setup, key management, root restriction, and connection procedures for ArmServe ARM64 Graviton instances.

---

## 1. Hardened SSH Configuration (`/etc/ssh/sshd_config.d/99-armserve-security.conf`)

ArmServe enforces zero-trust SSH access rules on all EC2 instances:

```text
# Hardened SSH Configuration for ArmServe Graviton Instances
Port 22
Protocol 2

# Disable Root Login
PermitRootLogin no

# Enforce Cryptographic Key Authentication
PubkeyAuthentication yes
AuthenticationMethods publickey

# Disable Insecure Password Authentication
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no

# Access Controls
AllowUsers appuser devops
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2

# Modern Ciphers & Message Authentication Codes (MACs)
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512
```

---

## 2. AWS Systems Manager (SSM) Session Manager Integration

AWS Systems Manager Session Manager is the **primary recommended remote administration channel**. It provides keyless, portless, fully audited shell sessions without opening SSH port 22 in Security Groups.

### Advantages of SSM Session Manager
- **Zero Open Inbound Ports**: Security Group does not require port 22 inbound access.
- **IAM Authorization**: Access is governed by AWS IAM policies (`ssm:StartSession`) rather than static SSH key pairs.
- **Session Audit Logging**: All shell commands and outputs are automatically streamed to Amazon S3 and AWS CloudWatch Log Groups (`/aws/ssm/armserve-sessions`).

---

## 3. Remote Connection Procedures

### Method A: AWS Systems Manager (Recommended & Preferred)

```bash
# 1. Ensure AWS CLI & Session Manager Plugin are installed
aws --version
session-manager-plugin --version

# 2. Start interactive Session Manager shell to Graviton instance
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --region us-east-1

# 3. SSH Tunnel via SSM (for port forwarding, e.g. web console or debugging)
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}'
```

### Method B: Key-Based SSH (Backup / Emergency Access)

```bash
# 1. Set strict permissions on private key
chmod 400 ~/.ssh/armserve-graviton-dev.pem

# 2. Connect using unprivileged user
ssh -i ~/.ssh/armserve-graviton-dev.pem appuser@<private-ip-or-bastion>
```

---

## 4. Key Management & Security Best Practices

1. **No Stored Private Keys**: Private keys are stored exclusively in AWS Secrets Manager or secure developer keychains; private keys must never be committed to Git.
2. **Short-Lived Ephemeral Keys**: SSH keys generated during automated trials are single-use and destroyed upon trial termination.
3. **Audit Trail**: Every SSM connection logs session activity to `/aws/ssm/armserve-sessions` CloudWatch Log Group.
