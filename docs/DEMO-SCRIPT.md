# Demo Walkthrough Script

This script provides a structured walkthrough for demonstrating the AWS Control Tower Automation tool, suitable for live demos, video recordings, or training sessions.

## Demo Setup (5 minutes)

### Prerequisites Check
- [ ] AWS account with admin permissions (management account)
- [ ] AWS CLI configured with credentials
- [ ] Python 3.12+ installed
- [ ] Tool downloaded and dependencies installed
- [ ] Clean AWS account (no existing Control Tower)

### Demo Environment
```bash
# Verify setup
aws sts get-caller-identity
python --version
ls -la config/config-example-*.yaml
```

## Demo Script (20-25 minutes)

### Introduction (2 minutes)

**"Today I'll show you how to deploy AWS Control Tower with a complete security baseline in under 90 minutes using this automation tool. We'll go from a basic AWS account to a fully governed multi-account environment with security services enabled."**

**Key points to mention:**
- Single command deployment
- Three security tiers (basic, standard, strict)
- Automated security baseline (GuardDuty, Security Hub, Config)
- Templates for different organization sizes

### Configuration Setup (3 minutes)

**"First, let's choose the right configuration template for our organization."**

```bash
# Show available templates
ls -la config/config-example-*.yaml

# Explain template differences
echo "Minimal: Single region, basic security - perfect for small orgs"
echo "Complete: Multi-region, standard security - most common choice"
echo "Enterprise: Global regions, strict security - for large enterprises"

# Copy template (use minimal for demo speed)
cp config/config-example-minimal.yaml config.yaml
```

**"The only required change is updating the email addresses for the two shared accounts."**

```bash
# Show what needs to be changed
grep -A 5 "accounts:" config.yaml
```

**Edit the config file (show in editor):**
- Change log_archive email to demo-logarchive@company.com
- Change audit email to demo-audit@company.com

### Prerequisites Validation (3 minutes)

**"Before deploying Control Tower, let's validate our AWS account is ready."**

```bash
# Run validation
python src/controltower-baseline.py --validate-only
```

**Expected output walkthrough:**
- ✅ AWS Credentials: Shows account ID and region
- ✅ AWS Organizations: Confirms all features enabled
- ❌ Organizations Structure: Expected - we haven't created OUs yet
- ❌ Account Structure: Expected - we need to create the shared accounts
- ⚠️ IAM Roles: Expected - Control Tower will create these
- ✅ Control Tower Status: Confirms no existing deployment

**"The validation shows what we expected - we need to set up the prerequisites first."**

### Interactive Deployment (12 minutes)

**"Now let's run the interactive deployment. The tool guides us through each step."**

```bash
# Start interactive mode
python src/controltower-baseline.py
```

#### Step 1: Validate Prerequisites (1 minute)
**"Let's start with option 1 to see the current status."**
- Select option 1
- Show the same validation results as before
- **"This confirms what we saw earlier - we need to set up prerequisites."**

#### Step 2: Setup Prerequisites (3 minutes)
**"Option 2 will automatically fix the prerequisite issues."**
- Select option 2
- **Explain what's happening:**
  - "Creating the Security OU for shared accounts"
  - "Creating Log Archive account with the email we specified"
  - "Creating Audit account with the email we specified"
  - "Setting up required IAM roles"
- **"This typically takes 3-5 minutes as AWS creates the accounts."**

#### Step 3: Deploy Control Tower (6 minutes)
**"Now for the main event - deploying Control Tower itself."**
- Select option 3
- **Explain the process:**
  - "Creating the Control Tower landing zone"
  - "This is the longest step - typically 60-90 minutes"
  - "We're applying the 'basic' security tier policies"
  - "Control Tower is setting up governance across our specified regions"

**For demo purposes (since this takes too long):**
- **"In a real deployment, we'd wait for this to complete"**
- **"Let me show you what the completed deployment looks like"**
- Switch to a pre-deployed environment or show screenshots

#### Step 4: Security Baseline (2 minutes)
**"After Control Tower completes, we enable the security baseline."**
- Select option 4 (or explain what it does)
- **Explain the security services:**
  - "GuardDuty for threat detection across all accounts"
  - "Security Hub for centralized security findings"
  - "AWS Config for compliance monitoring"
  - "All managed from the Audit account we created"

### Results Verification (3 minutes)

**"Let's verify everything worked by checking the AWS Console."**

#### Control Tower Console
- Navigate to Control Tower Console
- Show landing zone status: "Available"
- Show organizational structure with Security OU
- Show enrolled accounts

#### Organizations Console
- Show the organizational structure
- Point out the Security OU with Log Archive and Audit accounts
- Show applied Service Control Policies

#### Security Services
- **GuardDuty Console**: Show enabled status and member accounts
- **Security Hub Console**: Show enabled standards and compliance scores
- **Config Console**: Show configuration recording active

### Advanced Features Demo (2 minutes)

**"The tool also provides advanced security configuration management."**

```bash
# Return to interactive menu
python src/controltower-baseline.py
```

- Select option 5: Security Configuration Management
- **Show security tier options:**
  - "We can change from basic to standard or strict"
  - "We can set different tiers for different OUs"
  - "We can add account-level exceptions"

- Select option 7: Generate Documentation
- **Show generated documentation:**
  - "Architecture diagrams showing our setup"
  - "Configuration reports for compliance"

## Demo Wrap-up (2 minutes)

### Key Takeaways
**"In summary, we've accomplished in minutes what typically takes hours or days:"**

- ✅ **Deployed Control Tower** with proper organizational structure
- ✅ **Created shared accounts** (Log Archive, Audit) automatically
- ✅ **Applied security policies** appropriate for our organization size
- ✅ **Enabled security baseline** with GuardDuty, Security Hub, and Config
- ✅ **Established governance** across multiple AWS regions

### Next Steps
**"For ongoing operations, the tool provides:"**
- Monthly/quarterly maintenance checklists
- Troubleshooting playbooks for common issues
- Security policy management through the interactive menu
- Documentation generation for compliance reporting

### Questions and Discussion
**Common questions to be prepared for:**
- **"How long does this really take?"** 60-90 minutes for complete deployment
- **"Can we customize the security policies?"** Yes, through the security configuration menu
- **"What if we need to add more regions later?"** Update config and re-run deployment
- **"Is this safe for production?"** Yes, follows AWS best practices and Well-Architected principles

## Demo Variations

### For Technical Audiences
- Show more of the configuration file structure
- Explain the SCP policies in detail
- Demonstrate the troubleshooting capabilities
- Show the generated architecture diagrams

### For Business Audiences
- Focus on time savings and automation benefits
- Emphasize security and compliance features
- Show cost implications of different templates
- Highlight operational efficiency gains

### For Compliance Audiences
- Demonstrate the strict security tier
- Show Security Hub compliance dashboards
- Explain audit logging and monitoring
- Walk through the generated compliance reports

## Troubleshooting During Demo

### If Prerequisites Fail
- **Organizations not enabled**: Show how to enable through console
- **Permission issues**: Explain IAM requirements
- **Email conflicts**: Show how to use email aliases

### If Demo Environment Issues
- Have screenshots ready as backup
- Use a pre-deployed environment for verification steps
- Explain what would happen in a real deployment

### Technical Difficulties
- Have the troubleshooting guide ready
- Know the common error messages and solutions
- Be prepared to explain the manual steps if automation fails

## Post-Demo Resources

### For Attendees
- Link to Quick Start Guide
- Configuration templates
- Troubleshooting documentation
- Operations guide for day-2 activities

### Follow-up Materials
- Architecture diagrams
- Security policy comparisons
- Cost estimation worksheets
- Implementation timeline templates
