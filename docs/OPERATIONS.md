# Operations Guide

This guide covers day-2 operations for maintaining your Control Tower environment after initial deployment.

## Regular Maintenance Tasks

### Monthly Tasks (30 minutes)

#### Security Review
- [ ] **Review Security Hub findings**
  - Go to Security Hub Console → Findings
  - Address any HIGH or CRITICAL findings
  - Update suppression rules for false positives

- [ ] **Check GuardDuty alerts**
  - Go to GuardDuty Console → Findings
  - Investigate any HIGH or MEDIUM severity findings
  - Update threat intelligence if needed

- [ ] **Validate account compliance**
  - Run: `python src/controltower-baseline.py` → Option 6: Check Status
  - Verify all accounts are enrolled in Control Tower
  - Check for any drift in landing zone configuration

#### Account Management
- [ ] **Review new accounts**
  - Check AWS Organizations Console for new accounts
  - Ensure new accounts are in correct OUs
  - Verify security services are enabled for new accounts

- [ ] **Update contact information**
  - Verify email addresses are still valid
  - Update emergency contacts if staff changes occurred

### Quarterly Tasks (60 minutes)

#### Policy Review
- [ ] **Review SCP policies**
  - Run: `python src/controltower-baseline.py` → Option 5: Security Configuration
  - Assess if security tier is still appropriate
  - Review any OU overrides or account exceptions

- [ ] **Audit organizational structure**
  - Review OU structure for efficiency
  - Consider consolidating or splitting OUs based on growth
  - Update OU names if business units changed

#### Compliance and Reporting
- [ ] **Generate compliance reports**
  - Run: `python src/controltower-baseline.py` → Option 7: Generate Documentation
  - Review architecture diagrams for accuracy
  - Update documentation for any manual changes

- [ ] **Review access patterns**
  - Check CloudTrail logs for unusual access patterns
  - Review IAM roles and permissions
  - Update emergency access procedures

### Annual Tasks (2-3 hours)

#### Strategic Review
- [ ] **Assess Control Tower version**
  - Check for Control Tower landing zone updates
  - Plan upgrade if new features are beneficial
  - Test upgrades in non-production first

- [ ] **Review regional strategy**
  - Assess if additional regions are needed
  - Consider data residency requirements
  - Plan region expansion if needed

- [ ] **Security posture assessment**
  - Consider upgrading security tier (basic → standard → strict)
  - Review industry compliance requirements
  - Update security policies based on threat landscape

## Common Operational Tasks

### Adding New Accounts

#### Method 1: Through AWS Organizations Console
1. **Create the account**:
   - Go to AWS Organizations Console → Accounts → Add account
   - Provide unique email and account name
   - Wait for account creation (5-10 minutes)

2. **Move to correct OU**:
   - Select the new account
   - Choose "Move" → Select target OU
   - Wait for Control Tower enrollment (10-15 minutes)

3. **Verify enrollment**:
   - Run: `python src/controltower-baseline.py` → Option 6: Check Status
   - Confirm account appears in Control Tower dashboard
   - Verify security services are enabled

#### Method 2: Through Account Factory (Recommended)
1. **Use Control Tower Console**:
   - Go to Control Tower Console → Account Factory
   - Fill out account request form
   - Submit and wait for provisioning

2. **Automatic enrollment**:
   - Account is automatically enrolled in Control Tower
   - Security services are enabled automatically
   - Account is placed in specified OU

**Time required**: 15-30 minutes per account

### Changing Security Policies

#### Changing Global Security Tier
1. **Access security configuration**:
   ```bash
   python src/controltower-baseline.py
   # Select option 5: Security Configuration Management
   ```

2. **Select new tier**:
   - Choose "Change Security Tier"
   - Select: basic, standard, or strict
   - Confirm the change

3. **Verify deployment**:
   - Wait 10-15 minutes for policy propagation
   - Test access in a member account to verify restrictions

#### Adding OU-Specific Overrides
1. **Use security configuration menu**:
   - Option 5: Security Configuration Management
   - Choose "Set OU Override"
   - Select OU and desired security tier

2. **Common scenarios**:
   - Development OU → basic tier (more flexibility)
   - Production OU → strict tier (maximum security)
   - Sandbox OU → basic tier (testing freedom)

#### Adding Account Exceptions
1. **Use security configuration menu**:
   - Option 5: Security Configuration Management
   - Choose "Add Account Exception"
   - Specify account ID and policy to exempt

2. **Document exceptions**:
   - Keep a record of why exceptions were granted
   - Set review dates for temporary exceptions
   - Regular audit of all exceptions

### Managing Organizational Structure

#### Creating New OUs
1. **Plan the structure**:
   - Determine OU purpose and naming convention
   - Decide on parent OU (usually Root)
   - Consider future growth and account movement

2. **Create through AWS Console**:
   - Go to Organizations Console → Organize accounts
   - Select parent OU → Create organizational unit
   - Provide name and description

3. **Apply appropriate SCPs**:
   - Use security configuration menu to set OU-specific policies
   - Test policies with a test account first

#### Moving Accounts Between OUs
1. **Plan the move**:
   - Understand impact of different SCP policies
   - Coordinate with account owners
   - Plan for potential service disruptions

2. **Execute the move**:
   - Go to Organizations Console → Select account
   - Choose "Move" → Select destination OU
   - Monitor for any access issues

3. **Verify after move**:
   - Test critical applications in moved account
   - Verify security services still function
   - Update documentation and runbooks

### Monitoring and Alerting

#### Setting Up CloudWatch Alarms
```bash
# Example: Alert on Control Tower drift
aws cloudwatch put-metric-alarm \
  --alarm-name "ControlTower-Drift-Detected" \
  --alarm-description "Alert when Control Tower drift is detected" \
  --metric-name "DriftStatus" \
  --namespace "AWS/ControlTower" \
  --statistic "Maximum" \
  --period 300 \
  --threshold 1 \
  --comparison-operator "GreaterThanOrEqualToThreshold"
```

#### Regular Health Checks
1. **Weekly automated checks**:
   - Set up scheduled Lambda function to run status checks
   - Monitor Control Tower landing zone health
   - Check for account enrollment issues

2. **Monthly manual reviews**:
   - Review CloudTrail logs for unusual activity
   - Check Security Hub compliance scores
   - Verify GuardDuty is detecting threats appropriately

### Backup and Recovery

#### Configuration Backup
1. **Backup configuration files**:
   ```bash
   # Create backup directory
   mkdir -p backups/$(date +%Y-%m-%d)
   
   # Backup current configuration
   cp config.yaml backups/$(date +%Y-%m-%d)/
   cp config/security-config.yaml backups/$(date +%Y-%m-%d)/
   ```

2. **Document manual changes**:
   - Keep record of any manual changes made through AWS Console
   - Document reasons for changes and approval process
   - Update configuration files to reflect manual changes

#### Disaster Recovery Planning
1. **Control Tower recovery**:
   - Control Tower can be redeployed if needed
   - Account structure and SCPs can be recreated
   - Security services can be re-enabled

2. **Recovery procedures**:
   - Keep current configuration files in version control
   - Document all manual customizations
   - Test recovery procedures in non-production account

## Troubleshooting Operations

### Account Not Enrolling in Control Tower
**Symptoms**: New account created but not showing in Control Tower

**Solutions**:
1. Check account is in correct OU (not Root)
2. Verify Control Tower has permissions to manage the account
3. Try moving account to different OU and back
4. Contact AWS Support if issue persists

### SCP Policy Not Taking Effect
**Symptoms**: Policy changes not restricting access as expected

**Solutions**:
1. Wait 15-30 minutes for policy propagation
2. Check policy is attached to correct OU
3. Verify account is in the OU you think it is
4. Test with fresh AWS CLI session (clear cached credentials)

### Security Services Showing as Disabled
**Symptoms**: GuardDuty or Security Hub shows disabled for some accounts

**Solutions**:
1. Re-run post-deployment security setup:
   ```bash
   python src/controltower-baseline.py
   # Option 4: Post-Deployment Security Setup
   ```
2. Check delegated administrator account permissions
3. Verify accounts are enrolled in Control Tower first

## Best Practices

### Change Management
- [ ] Test all changes in non-production environment first
- [ ] Document all changes with business justification
- [ ] Implement approval process for security policy changes
- [ ] Schedule changes during maintenance windows

### Security
- [ ] Regular review of access patterns and permissions
- [ ] Monitor for unusual account creation or movement
- [ ] Keep security policies up to date with business needs
- [ ] Regular training for team members on Control Tower operations

### Documentation
- [ ] Keep runbooks updated with any process changes
- [ ] Document all customizations and exceptions
- [ ] Maintain contact lists for escalation procedures
- [ ] Regular review and update of operational procedures

## Escalation Procedures

### Internal Escalation
1. **Level 1**: Operations team handles routine tasks
2. **Level 2**: Senior engineers for complex issues or policy changes
3. **Level 3**: Architecture team for structural changes or major incidents

### AWS Support Escalation
- **Business hours**: Use AWS Support Console for non-urgent issues
- **After hours**: Use phone support for production-impacting issues
- **Critical**: Use emergency support for security incidents or major outages

### Emergency Contacts
- Maintain updated contact list for:
  - AWS account owners
  - Security team leads
  - Business stakeholders
  - AWS Technical Account Manager (if applicable)
