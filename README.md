# AWS Control Tower Automation

A simple, stable, and repeatable automation tool for AWS Control Tower deployment with complete security baseline configuration.

## Overview

This tool provides single-command deployment of AWS Control Tower with organization-wide security services including AWS Config, GuardDuty, and Security Hub. It follows AWS best practices and provides comprehensive validation and documentation.

## Features

- **Single Command Deployment**: Complete Control Tower + Security Baseline setup
- **Interactive Configuration**: Guided setup with safety confirmations
- **Security Baseline**: Automated Config, GuardDuty, and Security Hub deployment
- **SCP Tier System**: Basic, Standard, and Strict policy tiers
- **Comprehensive Validation**: End-to-end deployment verification
- **Automated Documentation**: Generated architecture diagrams and reports

## Quick Start with Templates

### Option 1: Interactive Template Setup (Recommended)
```bash
# Use the interactive template selector
python scripts/setup-config.py

# Validate configuration
python src/controltower-baseline.py --validate-only

# Deploy Control Tower
python src/controltower-baseline.py
```

### Option 2: Manual Template Selection
```bash
# Choose a template based on your needs:

# Minimal setup (single region, basic security)
cp config/config-example-minimal.yaml config.yaml

# Complete setup (multi-region, standard security)  
cp config/config-example-complete.yaml config.yaml

# Enterprise setup (global regions, strict security)
cp config/config-example-enterprise.yaml config.yaml

# Edit config.yaml with your email addresses and preferences
# Then run deployment
python src/controltower-baseline.py
```

### Available Templates

| Template | Use Case | Regions | Security | Features |
|----------|----------|---------|----------|----------|
| **Minimal** | Small orgs, PoC | Single | Basic | Essential only |
| **Complete** | Medium/Large orgs | Multi-region | Standard | Full features |
| **Enterprise** | Large enterprises | Global | Strict | Maximum security |

See `config/TEMPLATE-GUIDE.md` for detailed template documentation.

## Prerequisites

### AWS Requirements
- AWS Organizations enabled with all features
- Management account with appropriate permissions
- Python 3.12+ environment
- AWS CLI configured with credentials

### Required Permissions
The management account must have the following permissions:
- `AWSControlTowerServiceRolePolicy`
- `AWSOrganizationsFullAccess`
- `AWSConfigServiceRolePolicy`
- `AmazonGuardDutyFullAccess`
- `AWSSecurityHubFullAccess`

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/davidgendel/controltower-baseline-automation.git
   cd controltower-baseline-automation
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure AWS credentials**:
   ```bash
   aws configure
   # or use environment variables, IAM roles, etc.
   ```

## Configuration

### Option 1: Interactive Mode
Run without configuration file for guided setup:
```bash
python src/controltower-baseline.py
```

### Option 2: Configuration File
Create `config/settings.yaml`:
```yaml
aws:
  home_region: "us-east-1"
  governed_regions: ["us-east-1", "us-west-2"]

accounts:
  log_archive_name: "Log Archive"
  audit_name: "Audit"

organization:
  security_ou_name: "Security"
  sandbox_ou_name: "Sandbox"

scp_tier: "standard"  # basic|standard|strict

post_deployment:
  guardduty:
    enabled: true
    finding_publishing_frequency: "SIX_HOURS"
    delegated_admin_account: "audit"
  
  security_hub:
    enabled: true
    delegated_admin_account: "audit"
    default_standards: true
```

Then run:
```bash
python src/controltower-baseline.py config/settings.yaml
```

## Usage

### Interactive Menu
```
=== AWS Control Tower Automation ===
1. Validate Prerequisites
2. Deploy Control Tower
3. Post-Deployment Security Setup
4. Check Status
5. Generate Documentation
6. Configuration Management
0. Exit
```

### Step-by-Step Deployment

1. **Validate Prerequisites**:
   - Checks AWS Organizations setup
   - Verifies required IAM roles
   - Validates account structure

2. **Deploy Control Tower**:
   - Creates landing zone
   - Applies SCP tier policies
   - Monitors deployment status

3. **Security Baseline Setup**:
   - Configures AWS Config organization aggregator
   - Enables GuardDuty with delegated administration
   - Sets up Security Hub with compliance standards

4. **Validation & Documentation**:
   - Generates deployment validation report
   - Creates architecture diagrams
   - Produces configuration documentation

## SCP Tier System

### Basic Tier
- Minimal restrictions for development environments
- Allows most AWS services and actions
- Suitable for sandbox and development accounts

### Standard Tier (Recommended)
- Balanced security for production workloads
- Prevents common security misconfigurations
- Maintains operational flexibility

### Strict Tier
- Maximum security for regulated environments
- Comprehensive restrictions and compliance controls
- Suitable for highly regulated industries

## Validation

The tool provides comprehensive validation at multiple stages:

### Pre-deployment Validation
- AWS Organizations configuration
- Required IAM roles and permissions
- Account structure and naming

### Post-deployment Validation
- Control Tower landing zone status
- Security services configuration
- Account enrollment compliance

### Continuous Monitoring
- Service health checks
- Compliance status reporting
- Drift detection and remediation

## Architecture

The solution creates the following AWS architecture:

```
Management Account
├── Control Tower Landing Zone
├── AWS Organizations (All Features)
├── Organizational Units
│   ├── Security OU
│   │   ├── Log Archive Account
│   │   └── Audit Account
│   └── Sandbox OU
└── Service Control Policies (SCP Tier)

Security Baseline (Organization-wide)
├── AWS Config (Aggregated)
├── GuardDuty (Delegated Admin: Audit)
└── Security Hub (Delegated Admin: Audit)
```

## Troubleshooting

### Common Issues

#### Control Tower Deployment Fails
**Symptoms**: Landing zone creation fails or times out
**Solutions**:
1. Verify AWS Organizations has all features enabled
2. Check required IAM roles exist
3. Ensure no conflicting Control Tower deployment exists
4. Review CloudTrail logs for specific error messages

#### Security Services Not Enabled
**Symptoms**: GuardDuty or Security Hub not active organization-wide
**Solutions**:
1. Verify delegated administrator account permissions
2. Check service quotas and limits
3. Ensure accounts are enrolled in Control Tower
4. Review service-specific error logs

#### Account Enrollment Issues
**Symptoms**: Accounts not appearing in Control Tower
**Solutions**:
1. Verify account is in correct organizational unit
2. Check account factory prerequisites
3. Ensure account meets Control Tower requirements
4. Review enrollment status in Control Tower console

### Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| CT001 | Landing zone creation failed | Check prerequisites and retry |
| CT002 | SCP attachment failed | Verify organizational structure |
| SB001 | Config aggregator setup failed | Check Config service permissions |
| SB002 | GuardDuty delegation failed | Verify audit account permissions |
| SB003 | Security Hub setup failed | Check Security Hub service limits |

### Getting Help

1. **Check Logs**: Review application logs for detailed error messages
2. **AWS Console**: Verify service status in AWS Console
3. **Documentation**: Consult AWS Control Tower documentation
4. **Support**: Contact AWS Support for service-specific issues

## Security Considerations

### Least Privilege Access
- Use IAM roles with minimal required permissions
- Regularly review and audit access patterns
- Implement time-bound access where possible

### Network Security
- Deploy in private subnets where applicable
- Use VPC endpoints for AWS service communication
- Implement network segmentation and monitoring

### Data Protection
- Enable encryption at rest and in transit
- Use AWS KMS for key management
- Implement data classification and handling procedures

### Monitoring and Alerting
- Enable CloudTrail for all regions
- Configure GuardDuty for threat detection
- Set up Security Hub for compliance monitoring
- Implement custom alerting for critical events

## Maintenance

### Regular Tasks
- Review and update SCP policies
- Monitor compliance status
- Update security service configurations
- Review and rotate access credentials

### Updates and Patches
- Keep automation tool updated
- Monitor AWS service updates
- Test changes in non-production environments
- Maintain documentation and procedures

## Contributing

This tool follows strict development practices:

1. **Code Quality**: All code must pass PEP 8 compliance
2. **Testing**: Minimum 80% test coverage required
3. **Documentation**: Comprehensive docstrings and comments
4. **Security**: Follow AWS security best practices
5. **Validation**: All changes validated against AWS documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review AWS Control Tower documentation
3. Consult AWS Support for service-specific issues
4. Submit issues through the project repository

---

**Note**: This tool is designed for AWS Control Tower automation and should be used by experienced AWS administrators. Always test in non-production environments first.
