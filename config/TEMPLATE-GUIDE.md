# AWS Control Tower Automation - Template Guide

This directory contains pre-configured templates for different deployment scenarios. Choose the template that best matches your requirements and copy it to `config.yaml` in the project root.

## Available Configuration Templates

### 1. Minimal Configuration (`config-example-minimal.yaml`)
**Use Case**: Small organizations, proof of concept, or simple deployments
- Single region (us-east-1)
- Basic security tier
- Minimal organizational structure
- Essential accounts only

**Quick Start**:
```bash
cp config/config-example-minimal.yaml config.yaml
# Edit config.yaml with your email addresses
python src/controltower-baseline.py
```

### 2. Complete Configuration (`config-example-complete.yaml`)
**Use Case**: Medium to large organizations with comprehensive requirements
- Multi-region governance
- Standard security tier
- Full organizational structure
- All security services enabled
- Comprehensive documentation of all options

**Quick Start**:
```bash
cp config/config-example-complete.yaml config.yaml
# Edit config.yaml with your specific requirements
python src/controltower-baseline.py
```

### 3. Enterprise Configuration (`config-example-enterprise.yaml`)
**Use Case**: Large enterprises with strict security and compliance requirements
- Global multi-region coverage
- Strict security tier
- Comprehensive OU structure
- Enhanced security monitoring
- Enterprise-grade naming conventions

**Quick Start**:
```bash
cp config/config-example-enterprise.yaml config.yaml
# Edit config.yaml with your enterprise details
python src/controltower-baseline.py
```

## Available Manifest Templates

### 1. Default Manifest (`manifest-templates/default.json`)
- Standard two-region setup
- Basic organizational structure
- Standard retention policies

### 2. Minimal Manifest (`manifest-templates/minimal.json`)
- Single region deployment
- Minimal organizational structure
- Basic retention policies

### 3. Enterprise Manifest (`manifest-templates/enterprise.json`)
- Global multi-region coverage
- Comprehensive organizational structure
- Extended retention policies (7 years)

## Customization Guide

### Required Customizations
Before using any template, you **must** customize these fields:

1. **Email Addresses**: Update all email addresses to valid addresses in your organization
   ```yaml
   accounts:
     log_archive:
       email: "your-log-archive@yourcompany.com"
     audit:
       email: "your-audit@yourcompany.com"
   ```

2. **Home Region**: Ensure the home region matches your primary AWS region
   ```yaml
   aws:
     home_region: "your-preferred-region"
   ```

### Optional Customizations

1. **Organizational Units**: Modify the OU structure to match your organization
2. **Governed Regions**: Add or remove regions based on your global presence
3. **SCP Tier**: Choose security level (basic/standard/strict)
4. **Security Services**: Enable/disable specific security services

## SCP Tier Selection Guide

### Basic Tier
- **Use Case**: Development environments, proof of concept
- **Restrictions**: Minimal guardrails
- **Best For**: Learning, experimentation, non-production workloads

### Standard Tier (Recommended)
- **Use Case**: Production environments, balanced security
- **Restrictions**: Moderate guardrails with operational flexibility
- **Best For**: Most production workloads

### Strict Tier
- **Use Case**: Highly regulated environments, maximum security
- **Restrictions**: Comprehensive guardrails, limited operational flexibility
- **Best For**: Financial services, healthcare, government workloads

## Validation

After customizing your configuration, validate it before deployment:

```bash
# Validate configuration syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Validate prerequisites
python src/controltower-baseline.py --validate-only
```

## Support

For questions about template selection or customization:
1. Review the complete configuration template for all available options
2. Check the project documentation in `docs/`
3. Use the interactive mode for guided configuration
