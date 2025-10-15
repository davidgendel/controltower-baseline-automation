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

## Quick Start

**New to the tool?** See the [5-Minute Quick Start Guide](QUICKSTART.md) for the fastest path to deployment.

## Configuration Templates

### Template Selection
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

## Configuration Templates

The project includes three pre-configured templates designed for different organizational needs:

### Template Comparison

| Template | File | Use Case | Regions | Security | OUs | Setup Time |
|----------|------|----------|---------|----------|-----|------------|
| **Minimal** | `config-example-minimal.yaml` | Small orgs, PoC, testing | 1 (us-east-1) | Basic | 2 (default) | 30 min |
| **Complete** | `config-example-complete.yaml` | Medium/Large orgs | 3 (US + EU) | Standard | 4 OUs | 60 min |
| **Enterprise** | `config-example-enterprise.yaml` | Large enterprises | 6 (global) | Strict | 7 OUs | 90 min |

### Template Details

#### Minimal Template
- **Best for**: Organizations with < 50 accounts, proof of concepts, development environments
- **Regions**: Single region (us-east-1) for simplicity
- **Security**: Basic tier - minimal restrictions, maximum flexibility
- **Structure**: Default Control Tower OUs only (Security + Core)
- **Features**: Essential Control Tower functionality only

#### Complete Template  
- **Best for**: Medium to large organizations (50-200 accounts)
- **Regions**: Multi-region (us-east-1, us-west-2, eu-west-1) for production workloads
- **Security**: Standard tier - balanced security and operational flexibility
- **Structure**: 4 OUs (Security, Production, Development, Sandbox)
- **Features**: Full security baseline with GuardDuty, Security Hub, Config

#### Enterprise Template
- **Best for**: Large enterprises (200+ accounts), regulated industries
- **Regions**: Global coverage (6 regions across US, EU, Asia-Pacific)
- **Security**: Strict tier - maximum security controls and compliance
- **Structure**: 7 OUs (Security, Production, Staging, Development, Sandbox, Shared Services, Suspended)
- **Features**: Enhanced monitoring, compliance controls, region restrictions

### Template Usage

```bash
# Step 1: Choose and copy template
cp config/config-example-minimal.yaml config.yaml     # For small orgs
cp config/config-example-complete.yaml config.yaml    # For medium/large orgs  
cp config/config-example-enterprise.yaml config.yaml  # For enterprises

# Step 2: Edit email addresses (required)
nano config.yaml  # Update the email fields under 'accounts' section

# Step 3: Validate and deploy
python src/controltower-baseline.py --validate-only
python src/controltower-baseline.py
```

### Choosing the Right Template

#### Decision Tree
- **Small organization (< 50 accounts)** → Minimal template
- **Medium organization (50-200 accounts)** → Complete template  
- **Large enterprise (200+ accounts)** → Enterprise template
- **Regulated industry (finance, healthcare)** → Enterprise template
- **Development/testing only** → Minimal template
- **Multi-region production workloads** → Complete or Enterprise template
- **Global operations** → Enterprise template

#### Key Considerations
- **Compliance requirements**: Regulated industries should use Enterprise template with strict security
- **Geographic distribution**: Multi-region templates for global operations
- **Growth planning**: Choose template that accommodates 2-3 years of growth
- **Operational complexity**: Start with simpler templates and upgrade as needed

### Template Customization

All templates can be customized after copying:

#### Common Customizations
```yaml
# Change regions (add/remove as needed)
aws:
  governed_regions:
    - "us-east-1"
    - "your-preferred-region"

# Adjust security level
scp_tier: "basic"     # For development
scp_tier: "standard"  # For production (recommended)
scp_tier: "strict"    # For compliance

# Modify organizational structure
organization:
  additional_ous:
    - name: "YourCustomOU"
      parent: "Root"
```

#### Email Requirements
**Critical**: Each template requires unique email addresses for the two shared accounts:
```yaml
accounts:
  log_archive:
    email: "aws-log-archive@yourcompany.com"  # Must be globally unique
  audit:
    email: "aws-audit@yourcompany.com"        # Must be globally unique
```

**Email Tips**:
- Use email aliases: `admin+logarchive@company.com`
- Create dedicated AWS email addresses
- Ensure emails are accessible for AWS notifications

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
   git clone <repository-url>
   cd aws-management-automation
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

After running the tool, you'll see this menu:

```
=== AWS Control Tower Automation ===
1. Validate Prerequisites    ← Start here first
2. Setup Prerequisites       ← Fix any issues found
3. Deploy Control Tower      ← Main deployment
4. Post-Deployment Security Setup ← Enable security services
5. Security Configuration Management ← Adjust security policies
6. Check Status             ← Monitor progress
7. Generate Documentation   ← Create reports
8. Configuration Management ← Modify settings
0. Exit
```

**Recommended workflow**: Run options 1→2→3→4 in order for complete setup.

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

## Success Indicators

### How to Know It Worked

#### After Prerequisites (Steps 1-2)
✅ **You should see**: "All prerequisites validated successfully"  
✅ **AWS Console**: Organizations shows "All features" enabled  
❌ **If you see errors**: Run step 2 "Setup Prerequisites" to fix them

#### After Control Tower Deployment (Step 3)  
✅ **You should see**: "Landing zone deployment completed"  
✅ **AWS Console**: Control Tower dashboard shows green status  
✅ **Time taken**: 60-90 minutes for complete deployment  
❌ **If deployment fails**: Check [troubleshooting guide](docs/TROUBLESHOOTING.md)

#### After Security Setup (Step 4)
✅ **You should see**: "Security baseline deployment completed"  
✅ **AWS Console**: GuardDuty shows "X accounts protected"  
✅ **AWS Console**: Security Hub shows enabled with standards active  
✅ **Email**: You receive notifications about security findings  
❌ **If services aren't enabled**: Re-run step 4 or check troubleshooting guide

#### Final Verification
✅ **Control Tower Console**: Landing zone shows "Available" status  
✅ **Organizations Console**: Accounts are in correct OUs  
✅ **GuardDuty Console**: Shows member accounts and recent activity  
✅ **Security Hub Console**: Shows compliance scores and findings  
✅ **Config Console**: Shows configuration items being recorded

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

## Support and Documentation

### Getting Help
- **Setup Issues**: See [Quick Start Guide](QUICKSTART.md) and [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- **Configuration Questions**: See [Configuration Guide](docs/CONFIGURATION.md)
- **Day-2 Operations**: See [Operations Guide](docs/OPERATIONS.md)
- **AWS Service Issues**: Consult AWS Support for service-specific problems

### Additional Resources
- [Demo Walkthrough Script](docs/DEMO-SCRIPT.md) - For presentations and training
- [AWS Control Tower Documentation](https://docs.aws.amazon.com/controltower/) - Official AWS documentation
- [Developer Documentation](docs/DEVELOPER/) - For contributors and developers

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This tool is designed for AWS Control Tower automation and should be used by experienced AWS administrators. Always test in non-production environments first.
