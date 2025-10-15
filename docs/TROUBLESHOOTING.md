# Troubleshooting Playbook

This playbook provides quick solutions for common issues. For each problem, we show what it means, how to fix it, and how long it takes.

## Quick Diagnosis

### First Steps When Something Goes Wrong
```bash
# 1. Check if it's a configuration issue
python src/controltower-baseline.py --validate-only

# 2. Verify AWS access
aws sts get-caller-identity

# 3. Check AWS service health
# Visit: https://status.aws.amazon.com/
```

## Common Issues and Quick Fixes

### "Prerequisites validation failed"

**What it means**: Your AWS account isn't ready for Control Tower deployment

**Most common causes**:
- AWS Organizations not enabled with all features
- Missing required accounts (Log Archive, Audit)
- Insufficient IAM permissions

**Quick fix**:
1. Run the tool: `python src/controltower-baseline.py`
2. Select option **2: Setup Prerequisites**
3. Follow the prompts to fix each issue
4. Re-run option **1: Validate Prerequisites**

**Time to fix**: 5-10 minutes

---

### "Control Tower deployment failed"

**What it means**: AWS couldn't create the Control Tower landing zone

**Most common causes**:
- Another Control Tower deployment already exists
- Service quotas exceeded
- Region doesn't support Control Tower

**Quick fix**:
1. **Check for existing Control Tower**:
   - Go to AWS Console → Control Tower
   - If one exists, delete it first or use a different account

2. **Verify region support**:
   - Control Tower isn't available in all regions
   - Use us-east-1, us-west-2, or eu-west-1 for best support

3. **Check service quotas**:
   - Go to AWS Console → Service Quotas
   - Search for "Control Tower" and request increases if needed

**Time to fix**: 15-30 minutes

---

### "Security services not working"

**What it means**: GuardDuty, Security Hub, or Config didn't enable properly

**Most common causes**:
- Services already enabled in some accounts
- Delegated administrator conflicts
- Service quotas exceeded

**Quick fix**:
1. Run the tool: `python src/controltower-baseline.py`
2. Select option **4: Post-Deployment Security Setup**
3. If it fails again, try these steps:
   - Go to GuardDuty Console → Settings → Disable GuardDuty
   - Go to Security Hub Console → Settings → Disable Security Hub
   - Re-run option 4

**Time to fix**: 10-15 minutes

---

### "Email already in use"

**What it means**: The email addresses in your config are already used by other AWS accounts

**Quick fix**:
1. Edit your `config.yaml` file
2. Change the email addresses to unique ones:
   ```yaml
   accounts:
     log_archive:
       email: "your-unique-email+logarchive@company.com"
     audit:
       email: "your-unique-email+audit@company.com"
   ```
3. Use email aliases (the +suffix trick works with most email providers)

**Time to fix**: 2 minutes

---

### "Configuration file not found"

**What it means**: The tool can't find your configuration file

**Quick fix**:
1. Make sure you copied a template:
   ```bash
   cp config/config-example-minimal.yaml config.yaml
   ```
2. Or specify the config file directly:
   ```bash
   python src/controltower-baseline.py config/settings.yaml
   ```

**Time to fix**: 1 minute

---

### "Invalid YAML syntax"

**What it means**: There's a formatting error in your configuration file

**Quick fix**:
1. Check YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```
2. Common issues:
   - Mixed tabs and spaces (use spaces only)
   - Missing quotes around email addresses
   - Incorrect indentation

3. Copy a fresh template and start over if needed

**Time to fix**: 5 minutes

---

### "AWS credentials not configured"

**What it means**: The tool can't access your AWS account

**Quick fix**:
1. **Option 1 - AWS CLI**:
   ```bash
   aws configure
   # Enter your Access Key ID, Secret Key, and region
   ```

2. **Option 2 - Environment variables**:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export AWS_REGION="us-east-1"
   ```

3. **Option 3 - IAM roles** (if running on EC2):
   - Attach an IAM role with appropriate permissions to your EC2 instance

**Time to fix**: 3-5 minutes

## Interactive Menu Issues

### "Invalid choice" when selecting menu option 8

**What it means**: You're using an older version or the menu validation is broken

**Quick fix**: This should be fixed in the current version. If you still see this:
1. Make sure you're using the latest version
2. Try selecting option 0 to exit and restart the tool

---

### Menu appears but options don't work

**What it means**: There might be a Python import or dependency issue

**Quick fix**:
1. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Check Python version:
   ```bash
   python --version  # Should be 3.12 or higher
   ```

## AWS Console Verification

### How to Check if Control Tower Worked
1. **AWS Console → Control Tower**
   - Should show "Landing zone: Available"
   - Dashboard should be green with no errors

2. **AWS Console → Organizations**
   - Should show your organizational structure
   - Accounts should be in the correct OUs

3. **AWS Console → GuardDuty**
   - Should show "Enabled" status
   - Should list member accounts

4. **AWS Console → Security Hub**
   - Should show "Enabled" status
   - Should show security standards activated

### How to Check if Security Services Worked
1. **GuardDuty**: Go to GuardDuty Console → Summary
   - Should show "X accounts protected"
   - Should show recent activity (may take 15-30 minutes)

2. **Security Hub**: Go to Security Hub Console → Summary
   - Should show compliance scores
   - Should show findings from various sources

3. **Config**: Go to Config Console → Dashboard
   - Should show configuration items being recorded
   - Should show compliance status

## When to Contact AWS Support

Contact AWS Support if you encounter:
- Control Tower deployment fails repeatedly with the same error
- AWS service quotas that can't be increased through the console
- Billing or account-level issues
- Service outages affecting your region

## Prevention Tips

### Before You Start
- [ ] Verify you're in the management account (not a member account)
- [ ] Check that your AWS account is in good standing (no billing issues)
- [ ] Ensure you have admin-level permissions
- [ ] Test in a non-production account first

### Regular Maintenance
- [ ] Monitor AWS service health dashboard
- [ ] Keep the tool updated to the latest version
- [ ] Review and update email addresses if they change
- [ ] Backup your working configuration files

## Getting More Help

### Documentation
- [Quick Start Guide](../QUICKSTART.md) - Basic setup
- [Configuration Guide](CONFIGURATION.md) - Detailed configuration
- [Operations Guide](OPERATIONS.md) - Day-2 operations

### AWS Resources
- [AWS Control Tower User Guide](https://docs.aws.amazon.com/controltower/)
- [AWS Service Health Dashboard](https://status.aws.amazon.com/)
- [AWS Support Center](https://console.aws.amazon.com/support/)

### Community
- AWS re:Post forums for Control Tower questions
- AWS documentation feedback for service-specific issues
