# Quick Start Guide

## 5-Minute Setup

### For Small Organizations
```bash
# 1. Copy minimal template
cp config/config-example-minimal.yaml config.yaml

# 2. Edit email addresses (only required change)
nano config.yaml  # Update the two email fields

# 3. Deploy
python src/controltower-baseline.py
```

### For Enterprise Organizations  
```bash
# 1. Copy enterprise template
cp config/config-example-enterprise.yaml config.yaml

# 2. Customize for your organization
nano config.yaml  # Update emails, regions, OU names

# 3. Deploy
python src/controltower-baseline.py
```

## What Happens Next
1. Prerequisites validation (automatic)
2. Interactive menu appears
3. Follow the numbered steps 1→2→3→4
4. Complete deployment in 60-90 minutes

## Required Changes in config.yaml

### Minimal Setup
You only need to change these two email addresses:
```yaml
accounts:
  log_archive:
    email: "your-log-archive@yourcompany.com"  # ← Change this
  audit:
    email: "your-audit@yourcompany.com"        # ← Change this
```

### Enterprise Setup
Update these fields for your organization:
```yaml
accounts:
  log_archive:
    email: "your-log-archive@yourcompany.com"  # ← Change this
  audit:
    email: "your-audit@yourcompany.com"        # ← Change this

aws:
  governed_regions:                            # ← Add/remove regions as needed
    - "us-east-1"
    - "us-west-2" 
    - "eu-west-1"
```

## Interactive Menu Workflow

After running the tool, follow this sequence:

```
=== AWS Control Tower Automation ===
1. Validate Prerequisites    ← Start here first
2. Setup Prerequisites       ← Fix any issues found  
3. Deploy Control Tower      ← Main deployment
4. Post-Deployment Security  ← Enable security services
5. Security Configuration    ← Adjust security policies (optional)
6. Check Status             ← Monitor progress
7. Generate Documentation   ← Create reports (optional)
8. Configuration Management ← Modify settings (optional)
0. Exit
```

**Recommended workflow**: Run options 1→2→3→4 in order for complete setup.

## Success Indicators

### After Prerequisites (Steps 1-2)
✅ You should see: "All prerequisites validated successfully"
❌ If you see errors: Run step 2 to fix them

### After Control Tower Deployment (Step 3)  
✅ You should see: "Landing zone deployment completed"
✅ AWS Console shows: Control Tower dashboard with green status
❌ If deployment fails: Check [troubleshooting guide](docs/TROUBLESHOOTING.md)

### After Security Setup (Step 4)
✅ You should see: "Security baseline deployment completed"  
✅ AWS Console shows: GuardDuty and Security Hub enabled
✅ You receive: Email notifications about security findings

## Need Help?

- **Configuration questions**: See [Configuration Cookbook](docs/CONFIGURATION-COOKBOOK.md)
- **Something broke**: See [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- **Day-2 operations**: See [Operations Guide](docs/OPERATIONS.md)
