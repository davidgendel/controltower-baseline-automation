# Configuration Reference

This document provides practical configuration guidance for AWS Control Tower automation. For quick setup, see the [Quick Start Guide](../QUICKSTART.md).

## Configuration File Format

The tool uses YAML format. The default configuration file is `config/settings.yaml`.

## Working Configuration Example

Based on the actual implementation:

```yaml
# AWS Configuration - Core settings
aws:
  home_region: "us-east-1"
  governed_regions:
    - "us-east-1"
    - "us-west-2"
  profile_name: null  # Optional: AWS CLI profile name
  region_deny_enabled: false  # Optional: restrict to governed regions only

# Organization Configuration
organization:
  security_ou_name: "Security"
  additional_ous:
    - name: "Sandbox"
      parent: "Root"

# Account Configuration - Required for Control Tower
accounts:
  log_archive:
    name: "Log Archive"
    email: "aws-log-archive@yourcompany.com"  # Must be unique
  audit:
    name: "Audit"
    email: "aws-audit@yourcompany.com"        # Must be unique

# Security Policy Tier
scp_tier: "standard"  # Options: basic, standard, strict

# Identity Center (Optional)
identity_center:
  enabled: true

# Logging Configuration (Optional)
logging:
  cloudtrail_enabled: true
  config_enabled: true

# Post-Deployment Security Services
post_deployment:
  guardduty:
    enabled: true
    finding_publishing_frequency: "SIX_HOURS"
    delegated_admin_account: "audit"
    s3_protection: true
    kubernetes_protection: true
    malware_protection: true
  
  security_hub:
    enabled: true
    delegated_admin_account: "audit"
    auto_enable_new_accounts: true
    enable_default_standards: true
  
  aws_config:
    enabled: true
    organization_aggregator: true
    compliance_monitoring: true
```

## Security Configuration Management

The tool provides independent security policy management through a three-tier system, managed separately from the main deployment configuration.

### Security Tiers

#### Basic Tier
- **Use Case**: Development environments, testing, sandbox accounts
- **Restrictions**: Minimal - allows operational flexibility
- **Policies Applied**:
  - `deny_root_access`: Prevents root user access
  - `require_mfa`: Requires multi-factor authentication

#### Standard Tier (Recommended)
- **Use Case**: Production workloads, most organizations
- **Restrictions**: Balanced security without operational burden
- **Policies Applied**:
  - All Basic tier policies, plus:
  - `restrict_regions`: Limits access to governed regions only
  - `deny_leave_org`: Prevents accounts from leaving the organization

#### Strict Tier
- **Use Case**: Regulated industries (finance, healthcare), high-security environments
- **Restrictions**: Maximum security controls
- **Policies Applied**:
  - All Standard tier policies, plus:
  - `restrict_instance_types`: Limits EC2 instance types to approved list
  - `require_encryption`: Enforces encryption for storage and databases

### Security Configuration Structure

The security configuration is stored separately in `config/security-config.yaml`:

```yaml
security_tier: "standard"        # Global tier: basic, standard, strict
custom_policies: {}             # Custom policy definitions (advanced)
ou_overrides: {}               # OU-specific tier overrides
account_exceptions: []         # Account-level policy exceptions
```

### Management Interface

Security configuration is managed through the interactive menu:

1. Run the tool: `python src/controltower-baseline.py`
2. Select option **5: Security Configuration Management**
3. Choose from available options:
   - View current security tier and policies
   - Change global security tier
   - Set OU-specific overrides
   - Add account-level exceptions
   - List all available security tiers

### Common Security Scenarios

#### Scenario 1: Mixed Environment Security
```yaml
# Global standard security
security_tier: "standard"

# Development OU gets relaxed security
ou_overrides:
  "Development": "basic"

# Production OU gets strict security  
ou_overrides:
  "Production": "strict"
```

#### Scenario 2: Account Exceptions
```yaml
# Strict security organization-wide
security_tier: "strict"

# Specific accounts need exceptions
account_exceptions:
  - account_id: "123456789012"
    policy: "restrict_instance_types"
    reason: "ML workloads need GPU instances"
```

#### Scenario 3: Compliance Environment
```yaml
# Maximum security for compliance
security_tier: "strict"

# No overrides or exceptions
ou_overrides: {}
account_exceptions: []
```

## Configuration Sections

### AWS Configuration (`aws`)

#### Required Fields
- **`home_region`**: Primary AWS region for Control Tower deployment
  - Must be a region where Control Tower is available
  - Cannot be changed after deployment
  - Example: `"us-east-1"`

- **`governed_regions`**: List of regions under Control Tower governance
  - Must include the home region
  - Maximum 10 regions supported
  - Example: `["us-east-1", "us-west-2"]`

#### Optional Fields
- **`profile_name`**: AWS CLI profile for authentication
  - Default: `null` (uses default credential chain)
  - Example: `"production"`

- **`region_deny_enabled`**: Restrict access to non-governed regions
  - Default: `false`
  - Set to `true` for compliance environments
  - Creates SCP to deny access to other regions

### Account Configuration (`accounts`)

**Required**: Both accounts must be specified with unique email addresses.

```yaml
accounts:
  log_archive:
    name: "Log Archive"                    # Account display name
    email: "unique-email@yourcompany.com"  # Must be globally unique
  audit:
    name: "Audit"                          # Account display name  
    email: "another-email@yourcompany.com" # Must be globally unique
```

**Email Requirements**:
- Each AWS account requires a unique email address
- Use email aliases if needed: `user+logarchive@domain.com`
- Cannot reuse emails from existing AWS accounts

### Organization Configuration (`organization`)

#### Required Fields
- **`security_ou_name`**: Name for the Security organizational unit
  - Contains the Log Archive and Audit accounts
  - Example: `"Security"`

#### Optional Fields
- **`additional_ous`**: Extra organizational units to create
  ```yaml
  additional_ous:
    - name: "Production"
      parent: "Root"
    - name: "Development"
      parent: "Root"
  ```

### Security Policy Tier (`scp_tier`)

Controls the level of security restrictions applied organization-wide:

- **`"basic"`**: Minimal restrictions for development
  - Allows most AWS services and actions
  - Suitable for sandbox environments
  
- **`"standard"`**: Balanced security for production (recommended)
  - Prevents common security misconfigurations
  - Maintains operational flexibility
  
- **`"strict"`**: Maximum security for regulated environments
  - Comprehensive restrictions and compliance controls
  - Suitable for financial services, healthcare

### Post-Deployment Security (`post_deployment`)

#### GuardDuty Configuration
```yaml
guardduty:
  enabled: true                              # Enable GuardDuty organization-wide
  finding_publishing_frequency: "SIX_HOURS"  # Options: FIFTEEN_MINUTES, ONE_HOUR, SIX_HOURS
  delegated_admin_account: "audit"           # Which account manages GuardDuty
  s3_protection: true                        # Monitor S3 buckets
  kubernetes_protection: true                # Monitor EKS clusters
  malware_protection: true                   # Scan EC2 instances
```

#### Security Hub Configuration
```yaml
security_hub:
  enabled: true                        # Enable Security Hub organization-wide
  delegated_admin_account: "audit"     # Which account manages Security Hub
  auto_enable_new_accounts: true       # Automatically enable for new accounts
  enable_default_standards: true       # Enable AWS security standards
```

#### AWS Config Configuration
```yaml
aws_config:
  enabled: true                    # Enable Config organization-wide
  organization_aggregator: true    # Create organization-wide aggregator
  compliance_monitoring: true      # Enable compliance monitoring
```

## Environment Variable Overrides

The tool supports these environment variable overrides:

```bash
# AWS region override
export AWS_REGION="eu-west-1"

# AWS profile override  
export AWS_PROFILE="production"
```

**Precedence Order**:
1. Environment variables (highest)
2. Configuration file values
3. Default values (lowest)

## Configuration Templates

### Template Comparison

| Template | Use Case | Regions | Security | Setup Time |
|----------|----------|---------|----------|------------|
| **Minimal** | Small orgs, PoC | 1 region | Basic | 30 min |
| **Complete** | Medium/Large orgs | 3 regions | Standard | 60 min |
| **Enterprise** | Large enterprises | 6 regions | Strict | 90 min |

### Template Usage
```bash
# Copy desired template
cp config/config-example-minimal.yaml config.yaml

# Edit with your details
nano config.yaml

# Deploy
python src/controltower-baseline.py
```

## Common Configuration Patterns

### Multi-Region Production
```yaml
aws:
  home_region: "us-east-1"
  governed_regions: ["us-east-1", "us-west-2", "eu-west-1"]
scp_tier: "standard"
```

### Compliance Environment
```yaml
aws:
  region_deny_enabled: true
scp_tier: "strict"
post_deployment:
  guardduty:
    finding_publishing_frequency: "FIFTEEN_MINUTES"
```

### Development Environment
```yaml
aws:
  governed_regions: ["us-east-1"]  # Single region
scp_tier: "basic"                  # Minimal restrictions
```

## Validation

The tool validates configuration automatically:

- **Required fields**: Must be present and non-empty
- **Email uniqueness**: Checks for duplicate email addresses
- **Region validity**: Verifies AWS region names
- **Service availability**: Confirms services are available in selected regions

## Troubleshooting Configuration

### Common Issues

**"Invalid configuration format"**
- Check YAML syntax with `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`
- Ensure proper indentation (spaces, not tabs)

**"Email already in use"**
- Each account needs a globally unique email address
- Use email aliases: `user+audit@domain.com`

**"Region not supported"**
- Verify region supports Control Tower
- Check AWS Regional Services List

**"Home region not in governed regions"**
- The tool automatically adds home region to governed regions
- No action needed - this is handled automatically
