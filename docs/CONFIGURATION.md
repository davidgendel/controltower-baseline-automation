# Configuration Reference

This document provides comprehensive reference for all configuration parameters supported by the AWS Control Tower Automation tool.

## Configuration File Format

The tool uses YAML format for configuration files. The default configuration file is `config/settings.yaml`.

## Complete Configuration Example

```yaml
# AWS Configuration
aws:
  home_region: "us-east-1"
  governed_regions: 
    - "us-east-1"
    - "us-west-2"
  profile: "default"  # Optional: AWS CLI profile name

# Account Configuration
accounts:
  log_archive_name: "Log Archive"
  audit_name: "Audit"
  create_accounts: true  # Whether to create accounts if they don't exist

# Organization Configuration
organization:
  security_ou_name: "Security"
  sandbox_ou_name: "Sandbox"
  create_ous: true  # Whether to create OUs if they don't exist

# Service Control Policy Configuration
scp_tier: "standard"  # Options: basic, standard, strict

# Control Tower Configuration
control_tower:
  landing_zone_version: "3.3"  # Optional: specific version
  kms_key_arn: null  # Optional: custom KMS key
  access_logging:
    enabled: true
    bucket_name: null  # Optional: custom S3 bucket

# Post-Deployment Security Configuration
post_deployment:
  # AWS Config Configuration
  config:
    enabled: true
    delivery_channel_name: "default"
    configuration_recorder_name: "default"
    
  # GuardDuty Configuration
  guardduty:
    enabled: true
    finding_publishing_frequency: "SIX_HOURS"  # Options: FIFTEEN_MINUTES, ONE_HOUR, SIX_HOURS
    delegated_admin_account: "audit"
    enable_s3_protection: true
    enable_kubernetes_protection: true
    enable_malware_protection: true
    
  # Security Hub Configuration
  security_hub:
    enabled: true
    delegated_admin_account: "audit"
    enable_default_standards: true
    auto_enable_controls: true

# Documentation Configuration
documentation:
  enabled: true
  output_directory: "docs"
  generate_diagrams: true
  diagram_format: "png"  # Options: png, svg, pdf

# Validation Configuration
validation:
  enabled: true
  comprehensive: true
  generate_reports: true
  fail_on_warnings: false
```

## Configuration Sections

### AWS Configuration (`aws`)

#### `home_region` (Required)
- **Type**: String
- **Description**: Primary AWS region for Control Tower deployment
- **Example**: `"us-east-1"`
- **Constraints**: Must be a valid AWS region where Control Tower is available

#### `governed_regions` (Required)
- **Type**: List of strings
- **Description**: List of AWS regions to be governed by Control Tower
- **Example**: `["us-east-1", "us-west-2"]`
- **Constraints**: 
  - Must include the home region
  - Maximum 10 regions
  - All regions must support Control Tower

#### `profile` (Optional)
- **Type**: String
- **Description**: AWS CLI profile name for authentication
- **Default**: `"default"`
- **Example**: `"production"`

### Account Configuration (`accounts`)

#### `log_archive_name` (Required)
- **Type**: String
- **Description**: Name for the Log Archive account
- **Example**: `"Log Archive"`
- **Constraints**: Must be unique within the organization

#### `audit_name` (Required)
- **Type**: String
- **Description**: Name for the Audit account
- **Example**: `"Audit"`
- **Constraints**: Must be unique within the organization

#### `create_accounts` (Optional)
- **Type**: Boolean
- **Description**: Whether to create accounts if they don't exist
- **Default**: `true`
- **Example**: `false`

### Organization Configuration (`organization`)

#### `security_ou_name` (Required)
- **Type**: String
- **Description**: Name for the Security organizational unit
- **Example**: `"Security"`
- **Constraints**: Must be unique within the organization

#### `sandbox_ou_name` (Required)
- **Type**: String
- **Description**: Name for the Sandbox organizational unit
- **Example**: `"Sandbox"`
- **Constraints**: Must be unique within the organization

#### `create_ous` (Optional)
- **Type**: Boolean
- **Description**: Whether to create OUs if they don't exist
- **Default**: `true`
- **Example**: `false`

### SCP Tier Configuration (`scp_tier`)

#### SCP Tier Options
- **Type**: String (Enum)
- **Description**: Service Control Policy tier for security restrictions
- **Options**:
  - `"basic"`: Minimal restrictions for development
  - `"standard"`: Balanced security for production (recommended)
  - `"strict"`: Maximum security for regulated environments
- **Default**: `"standard"`

### Control Tower Configuration (`control_tower`)

#### `landing_zone_version` (Optional)
- **Type**: String
- **Description**: Specific Control Tower landing zone version
- **Default**: Latest available version
- **Example**: `"3.3"`

#### `kms_key_arn` (Optional)
- **Type**: String or null
- **Description**: Custom KMS key ARN for encryption
- **Default**: `null` (uses AWS managed keys)
- **Example**: `"arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"`

#### `access_logging` (Optional)
- **Type**: Object
- **Description**: Access logging configuration
- **Properties**:
  - `enabled` (Boolean): Enable access logging
  - `bucket_name` (String or null): Custom S3 bucket name

### Post-Deployment Configuration (`post_deployment`)

#### Config Configuration (`config`)

##### `enabled` (Optional)
- **Type**: Boolean
- **Description**: Enable AWS Config organization setup
- **Default**: `true`

##### `delivery_channel_name` (Optional)
- **Type**: String
- **Description**: Config delivery channel name
- **Default**: `"default"`

##### `configuration_recorder_name` (Optional)
- **Type**: String
- **Description**: Config recorder name
- **Default**: `"default"`

#### GuardDuty Configuration (`guardduty`)

##### `enabled` (Optional)
- **Type**: Boolean
- **Description**: Enable GuardDuty organization setup
- **Default**: `true`

##### `finding_publishing_frequency` (Optional)
- **Type**: String (Enum)
- **Description**: How often GuardDuty publishes findings
- **Options**: `"FIFTEEN_MINUTES"`, `"ONE_HOUR"`, `"SIX_HOURS"`
- **Default**: `"SIX_HOURS"`

##### `delegated_admin_account` (Required if enabled)
- **Type**: String
- **Description**: Account to use as GuardDuty delegated administrator
- **Example**: `"audit"`
- **Constraints**: Must be "audit" or "log_archive"

##### `enable_s3_protection` (Optional)
- **Type**: Boolean
- **Description**: Enable S3 protection in GuardDuty
- **Default**: `true`

##### `enable_kubernetes_protection` (Optional)
- **Type**: Boolean
- **Description**: Enable Kubernetes protection in GuardDuty
- **Default**: `true`

##### `enable_malware_protection` (Optional)
- **Type**: Boolean
- **Description**: Enable malware protection in GuardDuty
- **Default**: `true`

#### Security Hub Configuration (`security_hub`)

##### `enabled` (Optional)
- **Type**: Boolean
- **Description**: Enable Security Hub organization setup
- **Default**: `true`

##### `delegated_admin_account` (Required if enabled)
- **Type**: String
- **Description**: Account to use as Security Hub delegated administrator
- **Example**: `"audit"`
- **Constraints**: Must be "audit" or "log_archive"

##### `enable_default_standards` (Optional)
- **Type**: Boolean
- **Description**: Enable default security standards
- **Default**: `true`

##### `auto_enable_controls` (Optional)
- **Type**: Boolean
- **Description**: Automatically enable new controls
- **Default**: `true`

### Documentation Configuration (`documentation`)

#### `enabled` (Optional)
- **Type**: Boolean
- **Description**: Enable documentation generation
- **Default**: `true`

#### `output_directory` (Optional)
- **Type**: String
- **Description**: Directory for generated documentation
- **Default**: `"docs"`

#### `generate_diagrams` (Optional)
- **Type**: Boolean
- **Description**: Generate architecture diagrams
- **Default**: `true`

#### `diagram_format` (Optional)
- **Type**: String (Enum)
- **Description**: Format for generated diagrams
- **Options**: `"png"`, `"svg"`, `"pdf"`
- **Default**: `"png"`

### Validation Configuration (`validation`)

#### `enabled` (Optional)
- **Type**: Boolean
- **Description**: Enable deployment validation
- **Default**: `true`

#### `comprehensive` (Optional)
- **Type**: Boolean
- **Description**: Perform comprehensive validation checks
- **Default**: `true`

#### `generate_reports` (Optional)
- **Type**: Boolean
- **Description**: Generate validation reports
- **Default**: `true`

#### `fail_on_warnings` (Optional)
- **Type**: Boolean
- **Description**: Treat warnings as failures
- **Default**: `false`

## Environment Variable Overrides

Configuration values can be overridden using environment variables with the prefix `CT_`:

```bash
# Override home region
export CT_AWS_HOME_REGION="eu-west-1"

# Override SCP tier
export CT_SCP_TIER="strict"

# Override GuardDuty settings
export CT_POST_DEPLOYMENT_GUARDDUTY_ENABLED="false"
```

### Environment Variable Naming Convention

Environment variables follow this pattern:
- Prefix: `CT_`
- Section and key names in uppercase
- Nested keys separated by underscores
- Arrays specified as comma-separated values

Examples:
- `aws.home_region` → `CT_AWS_HOME_REGION`
- `post_deployment.guardduty.enabled` → `CT_POST_DEPLOYMENT_GUARDDUTY_ENABLED`
- `aws.governed_regions` → `CT_AWS_GOVERNED_REGIONS="us-east-1,us-west-2"`

## Configuration Validation

The tool performs comprehensive configuration validation:

### Required Fields
- All required fields must be present
- Values must match expected types
- Enum values must be from allowed options

### AWS-Specific Validation
- Regions must be valid AWS regions
- Account names must be unique
- Service availability checked per region

### Cross-Field Validation
- Home region must be in governed regions list
- Delegated admin accounts must exist
- SCP tier must be compatible with organization type

### Security Validation
- No sensitive data in configuration files
- Proper IAM role references
- Secure default values

## Configuration Examples

### Minimal Configuration
```yaml
aws:
  home_region: "us-east-1"
  governed_regions: ["us-east-1"]

accounts:
  log_archive_name: "Log Archive"
  audit_name: "Audit"

organization:
  security_ou_name: "Security"
  sandbox_ou_name: "Sandbox"

scp_tier: "standard"
```

### Multi-Region Production Configuration
```yaml
aws:
  home_region: "us-east-1"
  governed_regions: 
    - "us-east-1"
    - "us-west-2"
    - "eu-west-1"

accounts:
  log_archive_name: "Production-LogArchive"
  audit_name: "Production-Audit"

organization:
  security_ou_name: "Production-Security"
  sandbox_ou_name: "Production-Sandbox"

scp_tier: "strict"

post_deployment:
  guardduty:
    finding_publishing_frequency: "FIFTEEN_MINUTES"
    enable_s3_protection: true
    enable_kubernetes_protection: true
    enable_malware_protection: true
  
  security_hub:
    enable_default_standards: true
    auto_enable_controls: true
```

### Development Environment Configuration
```yaml
aws:
  home_region: "us-west-2"
  governed_regions: ["us-west-2"]

accounts:
  log_archive_name: "Dev-LogArchive"
  audit_name: "Dev-Audit"

organization:
  security_ou_name: "Dev-Security"
  sandbox_ou_name: "Dev-Sandbox"

scp_tier: "basic"

post_deployment:
  guardduty:
    finding_publishing_frequency: "SIX_HOURS"
  
validation:
  fail_on_warnings: false
```

## Best Practices

### Configuration Management
1. **Version Control**: Store configuration files in version control
2. **Environment Separation**: Use separate configs for dev/staging/prod
3. **Sensitive Data**: Use environment variables for sensitive values
4. **Validation**: Always validate configuration before deployment

### Security Considerations
1. **Least Privilege**: Use minimal required permissions
2. **Encryption**: Enable encryption for all supported services
3. **Monitoring**: Enable comprehensive logging and monitoring
4. **Regular Reviews**: Periodically review and update configurations

### Operational Excellence
1. **Documentation**: Document all configuration changes
2. **Testing**: Test configuration changes in non-production first
3. **Backup**: Maintain backup copies of working configurations
4. **Automation**: Use CI/CD for configuration deployment where possible
