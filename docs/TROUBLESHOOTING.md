# Troubleshooting Guide

This guide provides solutions for common issues encountered when using the AWS Control Tower Automation tool.

## Quick Diagnosis

### Check System Status
```bash
# Run validation to check current status
python src/controltower-baseline.py --validate-only

# Check AWS credentials
aws sts get-caller-identity

# Verify region availability
aws controltower get-landing-zone --region us-east-1
```

### Common Error Patterns
- **Permission Errors**: Usually indicate missing IAM permissions
- **Service Unavailable**: Check AWS service health and region availability
- **Configuration Errors**: Validate configuration file syntax and values
- **Network Errors**: Verify internet connectivity and AWS endpoint access

## Prerequisites Issues

### AWS Organizations Not Enabled
**Error**: `Organizations service is not available or not enabled`

**Symptoms**:
- Cannot access Organizations APIs
- Error during prerequisites validation
- "All features not enabled" message

**Solutions**:
1. **Enable AWS Organizations**:
   ```bash
   aws organizations create-organization --feature-set ALL
   ```

2. **Verify Organization Status**:
   ```bash
   aws organizations describe-organization
   ```

3. **Check Permissions**:
   - Ensure account has `AWSOrganizationsFullAccess`
   - Verify you're in the management account

### Missing IAM Roles
**Error**: `Required IAM role not found: AWSControlTowerAdmin`

**Symptoms**:
- Control Tower deployment fails
- Permission denied errors
- Role assumption failures

**Solutions**:
1. **Create Required Roles**:
   ```bash
   # Run prerequisites setup
   python src/controltower-baseline.py --setup-prerequisites
   ```

2. **Manual Role Creation**:
   - Navigate to IAM Console
   - Create roles with Control Tower service trust policy
   - Attach required policies

3. **Verify Role Policies**:
   ```bash
   aws iam get-role --role-name AWSControlTowerAdmin
   aws iam list-attached-role-policies --role-name AWSControlTowerAdmin
   ```

### Account Creation Issues
**Error**: `Cannot create account: Email already in use`

**Symptoms**:
- Account creation fails
- Duplicate email address errors
- Account factory issues

**Solutions**:
1. **Use Unique Email Addresses**:
   - Each AWS account requires unique email
   - Use email aliases (e.g., `user+logarchive@domain.com`)

2. **Check Existing Accounts**:
   ```bash
   aws organizations list-accounts
   ```

3. **Use Existing Accounts**:
   - Update configuration to reference existing accounts
   - Set `create_accounts: false` in configuration

## Control Tower Deployment Issues

### Landing Zone Creation Fails
**Error**: `Landing zone creation failed with status: FAILED`

**Symptoms**:
- Deployment hangs or fails
- CloudFormation stack errors
- Resource creation timeouts

**Solutions**:
1. **Check Prerequisites**:
   ```bash
   # Validate all prerequisites
   python src/controltower-baseline.py --validate-prerequisites
   ```

2. **Review CloudFormation Events**:
   - Navigate to CloudFormation Console
   - Check Control Tower stack events
   - Look for specific error messages

3. **Common Fixes**:
   - Ensure no existing Control Tower deployment
   - Verify sufficient service quotas
   - Check for conflicting resources

4. **Retry Deployment**:
   ```bash
   # Clean up failed deployment first
   aws controltower delete-landing-zone --landing-zone-identifier <id>
   
   # Wait for cleanup completion, then retry
   python src/controltower-baseline.py --deploy-control-tower
   ```

### SCP Attachment Failures
**Error**: `Failed to attach SCP policy to organizational unit`

**Symptoms**:
- Policy attachment errors
- Permission denied for SCP operations
- Organizational unit not found

**Solutions**:
1. **Verify OU Structure**:
   ```bash
   aws organizations list-organizational-units-for-parent --parent-id <root-id>
   ```

2. **Check SCP Permissions**:
   - Ensure `AWSOrganizationsFullAccess` permission
   - Verify SCP policies are enabled

3. **Manual SCP Management**:
   - Navigate to Organizations Console
   - Manually attach policies to OUs
   - Verify policy syntax and content

### Drift Detection Issues
**Error**: `Landing zone drift detected`

**Symptoms**:
- Configuration drift warnings
- Manual changes detected
- Compliance violations

**Solutions**:
1. **Review Drift Details**:
   ```bash
   aws controltower get-landing-zone --include-drift
   ```

2. **Reset to Baseline**:
   - Use Control Tower Console to reset
   - Or redeploy with current configuration

3. **Prevent Future Drift**:
   - Use SCPs to prevent manual changes
   - Implement change management processes

## Security Services Issues

### AWS Config Setup Failures
**Error**: `Config organization aggregator setup failed`

**Symptoms**:
- Config not enabled organization-wide
- Aggregator creation failures
- Permission errors

**Solutions**:
1. **Check Config Service Role**:
   ```bash
   aws iam get-role --role-name AWSConfigRole
   ```

2. **Verify Aggregator Permissions**:
   - Ensure Config has organization permissions
   - Check cross-account access

3. **Manual Config Setup**:
   ```bash
   # Enable Config in management account
   aws configservice put-configuration-recorder --configuration-recorder name=default,roleARN=<role-arn>
   
   # Create organization aggregator
   aws configservice put-organization-configuration-aggregator --organization-aggregator-name OrgAggregator
   ```

### GuardDuty Delegation Issues
**Error**: `GuardDuty delegated administrator setup failed`

**Symptoms**:
- Cannot set delegated administrator
- GuardDuty not enabled organization-wide
- Member account invitation failures

**Solutions**:
1. **Verify Account Status**:
   ```bash
   aws guardduty list-detectors
   aws organizations describe-account --account-id <audit-account-id>
   ```

2. **Enable GuardDuty in Management Account**:
   ```bash
   aws guardduty create-detector --enable
   ```

3. **Set Delegated Administrator**:
   ```bash
   aws organizations register-delegated-administrator \
     --account-id <audit-account-id> \
     --service-principal guardduty.amazonaws.com
   ```

4. **Check Service Quotas**:
   - Verify GuardDuty member account limits
   - Request quota increases if needed

### Security Hub Configuration Issues
**Error**: `Security Hub organization setup failed`

**Symptoms**:
- Security Hub not enabled
- Standards not activated
- Finding aggregation failures

**Solutions**:
1. **Enable Security Hub**:
   ```bash
   aws securityhub enable-security-hub
   ```

2. **Set Organization Configuration**:
   ```bash
   aws securityhub create-configuration-policy \
     --name OrgPolicy \
     --configuration-policy <policy-json>
   ```

3. **Enable Standards**:
   ```bash
   aws securityhub batch-enable-standards \
     --standards-subscription-requests StandardsArn=<arn>
   ```

## Validation and Documentation Issues

### Validation Failures
**Error**: `Deployment validation failed: Service not responding`

**Symptoms**:
- Validation checks fail
- Services appear inactive
- Status checks timeout

**Solutions**:
1. **Check Service Health**:
   ```bash
   # Check individual services
   aws controltower get-landing-zone
   aws guardduty list-detectors
   aws securityhub describe-hub
   ```

2. **Wait for Propagation**:
   - Some services take time to propagate
   - Wait 10-15 minutes and retry validation

3. **Manual Verification**:
   - Use AWS Console to verify service status
   - Check service-specific dashboards

### Documentation Generation Failures
**Error**: `Documentation generation failed: Template not found`

**Symptoms**:
- Missing documentation files
- Template processing errors
- Diagram generation failures

**Solutions**:
1. **Check Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify Output Directory**:
   ```bash
   mkdir -p docs
   chmod 755 docs
   ```

3. **Manual Documentation**:
   ```bash
   # Generate documentation manually
   python src/controltower-baseline.py --generate-docs-only
   ```

## Network and Connectivity Issues

### AWS API Connectivity
**Error**: `Unable to connect to AWS services`

**Symptoms**:
- Network timeouts
- SSL/TLS errors
- DNS resolution failures

**Solutions**:
1. **Check Internet Connectivity**:
   ```bash
   ping aws.amazon.com
   nslookup controltower.us-east-1.amazonaws.com
   ```

2. **Verify AWS Endpoints**:
   ```bash
   curl -I https://controltower.us-east-1.amazonaws.com
   ```

3. **Configure Proxy Settings**:
   ```bash
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

4. **Use VPC Endpoints**:
   - Configure VPC endpoints for AWS services
   - Update route tables and security groups

### Region Availability Issues
**Error**: `Service not available in region: eu-north-1`

**Symptoms**:
- Service unavailable errors
- Region-specific failures
- Feature not supported messages

**Solutions**:
1. **Check Service Availability**:
   - Consult AWS Regional Services List
   - Verify Control Tower region support

2. **Update Configuration**:
   ```yaml
   aws:
     governed_regions: 
       - "us-east-1"  # Use supported regions only
       - "us-west-2"
   ```

3. **Use Alternative Regions**:
   - Choose regions with full service support
   - Consider data residency requirements

## Performance Issues

### Slow Deployment Times
**Symptoms**:
- Deployment takes longer than expected
- API calls timing out
- Progress appears stuck

**Solutions**:
1. **Check AWS Service Health**:
   - Visit AWS Service Health Dashboard
   - Look for service disruptions

2. **Optimize Configuration**:
   ```yaml
   # Reduce governed regions for faster deployment
   aws:
     governed_regions: ["us-east-1"]  # Start with single region
   ```

3. **Monitor Progress**:
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   python src/controltower-baseline.py
   ```

### Memory or Resource Issues
**Symptoms**:
- Out of memory errors
- Process crashes
- System resource exhaustion

**Solutions**:
1. **Increase System Resources**:
   - Use larger EC2 instance
   - Increase available memory
   - Monitor disk space

2. **Optimize Processing**:
   ```bash
   # Process in smaller batches
   export CT_BATCH_SIZE=10
   ```

## Error Code Reference

### Control Tower Errors (CT-xxx)
- **CT-001**: Landing zone creation failed
- **CT-002**: SCP attachment failed
- **CT-003**: Drift detection error
- **CT-004**: Account enrollment failed

### Security Baseline Errors (SB-xxx)
- **SB-001**: Config aggregator setup failed
- **SB-002**: GuardDuty delegation failed
- **SB-003**: Security Hub setup failed
- **SB-004**: Service health check failed

### Configuration Errors (CF-xxx)
- **CF-001**: Invalid configuration format
- **CF-002**: Missing required parameter
- **CF-003**: Invalid parameter value
- **CF-004**: Configuration validation failed

### Permission Errors (PM-xxx)
- **PM-001**: Insufficient IAM permissions
- **PM-002**: Role assumption failed
- **PM-003**: Cross-account access denied
- **PM-004**: Service-linked role missing

## Getting Additional Help

### Log Analysis
1. **Enable Debug Logging**:
   ```bash
   export LOG_LEVEL=DEBUG
   python src/controltower-baseline.py 2>&1 | tee deployment.log
   ```

2. **Check CloudTrail Logs**:
   - Review API calls in CloudTrail
   - Look for error patterns and failed operations

3. **AWS Support**:
   - Open AWS Support case for service-specific issues
   - Include relevant log excerpts and error messages

### Community Resources
- **AWS Documentation**: Latest Control Tower documentation
- **AWS Forums**: Community discussions and solutions
- **GitHub Issues**: Report bugs and feature requests

### Professional Support
- **AWS Professional Services**: For complex deployments
- **AWS Partners**: Certified implementation partners
- **Training**: AWS Control Tower workshops and training

## Prevention Strategies

### Pre-Deployment Checklist
- [ ] Verify AWS Organizations is enabled with all features
- [ ] Confirm sufficient permissions in management account
- [ ] Check service quotas and limits
- [ ] Validate configuration file syntax
- [ ] Test in non-production environment first

### Monitoring and Alerting
- [ ] Set up CloudWatch alarms for service health
- [ ] Configure SNS notifications for failures
- [ ] Implement regular validation checks
- [ ] Monitor AWS service health dashboard

### Change Management
- [ ] Document all configuration changes
- [ ] Test changes in development environment
- [ ] Use version control for configuration files
- [ ] Implement approval process for production changes

### Regular Maintenance
- [ ] Review and update SCP policies
- [ ] Monitor compliance status
- [ ] Update tool to latest version
- [ ] Review and rotate access credentials
