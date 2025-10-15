"""Automated Markdown documentation generation for Control Tower deployment.

This module handles generation of deployment summaries, configuration documentation,
and validation reports with consistent formatting and comprehensive content.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import logging

from src.core.config import Configuration
from src.core.aws_client import AWSClientManager


logger = logging.getLogger(__name__)


class DocumentationError(Exception):
    """Raised when documentation generation fails."""
    pass


class DocumentationGenerator:
    """Automated Markdown documentation generation for Control Tower deployment."""
    
    def __init__(self, config: Configuration, aws_client: AWSClientManager):
        """Initialize documentation generator.
        
        Args:
            config: Configuration instance
            aws_client: AWS client manager instance
        """
        self.config = config
        self.aws_client = aws_client
        
    def generate_deployment_summary(self, deployment_state: Dict[str, Any]) -> str:
        """Generate comprehensive deployment summary report.
        
        Args:
            deployment_state: Current deployment state with configuration and status
            
        Returns:
            Formatted Markdown deployment summary report
            
        Raises:
            DocumentationError: When report generation fails
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            summary = f"""# AWS Control Tower Deployment Summary

**Generated**: {timestamp}  
**Account**: {self.aws_client.account_id}  
**Region**: {self.config.get_home_region()}

## Configuration Overview

| Parameter | Value |
|-----------|-------|
| Home Region | {self.config.get_home_region()} |
| Governed Regions | {', '.join(self.config.get_governed_regions())} |
| SCP Tier | {self.config.get_scp_tier()} |

## Deployment Status

"""
            
            # Add deployment status for each component
            for component, status in deployment_state.items():
                if isinstance(status, dict) and 'status' in status:
                    icon = "✅" if status['status'] == 'success' else "❌"
                    summary += f"- **{component.replace('_', ' ').title()}**: {icon} {status['status']}\n"
            
            summary += "\n## Next Steps\n\n"
            summary += "- Monitor AWS Console for deployment progress\n"
            summary += "- Review security services configuration\n"
            summary += "- Validate account enrollment and compliance\n"
            
            return summary
            
        except Exception as e:
            raise DocumentationError(f"Failed to generate deployment summary: {e}")
    
    def generate_configuration_docs(self) -> str:
        """Generate configuration documentation from YAML schema.
        
        Returns:
            Formatted Markdown configuration documentation
            
        Raises:
            DocumentationError: When configuration documentation generation fails
        """
        try:
            docs = """# Configuration Reference

## AWS Configuration

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `aws.home_region` | Primary AWS region | `us-east-1` |
| `aws.governed_regions` | List of governed regions | `["us-east-1", "us-west-2"]` |

### Optional Parameters

| Parameter | Description | Default | Options |
|-----------|-------------|---------|---------|
| `scp_tier` | SCP security tier | `standard` | `basic`, `standard`, `strict` |

## Example Configuration

```yaml
aws:
  home_region: "us-east-1"
  governed_regions: ["us-east-1", "us-west-2"]

scp_tier: "standard"

post_deployment:
  guardduty:
    enabled: true
    finding_publishing_frequency: "SIX_HOURS"
  security_hub:
    enabled: true
    default_standards: true
```

## Validation Rules

- Home region must be included in governed regions
- SCP tier must be one of: basic, standard, strict
- All regions must be valid AWS region identifiers
"""
            
            return docs
            
        except Exception as e:
            raise DocumentationError(f"Failed to generate configuration docs: {e}")
    
    def generate_validation_report(self, validation_results: Dict[str, Any]) -> str:
        """Generate validation report with service health and compliance status.
        
        Args:
            validation_results: Validation results from deployment validator
            
        Returns:
            Formatted Markdown validation report
            
        Raises:
            DocumentationError: When validation report generation fails
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            report = f"""# Deployment Validation Report

**Generated**: {timestamp}  
**Overall Status**: {"✅ PASSED" if validation_results.get('overall_healthy', False) else "❌ FAILED"}

## Service Health Status

"""
            
            # Add service status details
            for service, status in validation_results.items():
                if service != 'overall_healthy' and isinstance(status, dict):
                    service_name = service.replace('_', ' ').title()
                    overall_status = status.get('overall_healthy', False)
                    icon = "✅" if overall_status else "❌"
                    
                    report += f"### {service_name} {icon}\n\n"
                    
                    for check, result in status.items():
                        if check != 'overall_healthy':
                            check_icon = "✅" if result else "❌"
                            check_name = check.replace('_', ' ').title()
                            report += f"- **{check_name}**: {check_icon}\n"
                    
                    report += "\n"
            
            report += "## Remediation Steps\n\n"
            
            if not validation_results.get('overall_healthy', False):
                report += "Review failed checks above and:\n"
                report += "1. Check AWS Console for service status\n"
                report += "2. Verify IAM permissions and service access\n"
                report += "3. Re-run deployment if necessary\n"
            else:
                report += "All services are healthy. No action required.\n"
            
            return report
            
        except Exception as e:
            raise DocumentationError(f"Failed to generate validation report: {e}")
    
    def save_documentation(self, content: str, filename: str, output_dir: Path = None) -> Path:
        """Save documentation content to file.
        
        Args:
            content: Documentation content to save
            filename: Name of the output file
            output_dir: Output directory (defaults to docs/)
            
        Returns:
            Path to the saved documentation file
            
        Raises:
            DocumentationError: When file save operation fails
        """
        try:
            if output_dir is None:
                output_dir = Path("docs")
            
            output_dir.mkdir(exist_ok=True)
            file_path = output_dir / filename
            
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"Documentation saved to {file_path}")
            
            return file_path
            
        except Exception as e:
            raise DocumentationError(f"Failed to save documentation: {e}")
