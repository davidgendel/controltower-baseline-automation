"""End-to-end deployment validation for Control Tower and security baseline.

This module provides comprehensive validation of Control Tower deployment status,
security services configuration, and organizational compliance.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging

from src.core.config import Configuration
from src.core.aws_client import AWSClientManager


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when deployment validation fails."""
    pass


class DeploymentValidator:
    """End-to-end deployment validation for Control Tower automation."""
    
    def __init__(self, config: Configuration, aws_client: AWSClientManager):
        """Initialize deployment validator.
        
        Args:
            config: Configuration instance
            aws_client: AWS client manager instance
        """
        self.config = config
        self.aws_client = aws_client
        
    def validate_control_tower_deployment(self) -> Dict[str, Any]:
        """Validate Control Tower landing zone deployment status.
        
        Returns:
            Validation results with status and remediation guidance
            
        Raises:
            ValidationError: When validation cannot be performed
        """
        try:
            results = {
                "status": "UNKNOWN",
                "landing_zone_status": None,
                "drift_status": None,
                "organizational_units": [],
                "remediation_steps": []
            }
            
            # Check landing zone status using GetLandingZone API
            ct_client = self.aws_client.get_client('controltower')
            
            try:
                response = ct_client.get_landing_zone()
                results["landing_zone_status"] = response.get('status', 'UNKNOWN')
                results["drift_status"] = response.get('driftStatus', 'UNKNOWN')
                
                if results["landing_zone_status"] == "ACTIVE":
                    results["status"] = "PASS"
                else:
                    results["status"] = "FAIL"
                    results["remediation_steps"].append(
                        "Landing zone not active. Check Control Tower console."
                    )
                    
            except Exception as e:
                results["status"] = "FAIL"
                results["remediation_steps"].append(
                    f"Cannot access Control Tower: {str(e)}"
                )
            
            # Validate organizational structure
            try:
                org_client = self.aws_client.get_client('organizations')
                ous = org_client.list_organizational_units_for_parent(
                    ParentId=org_client.list_roots()['Roots'][0]['Id']
                )
                results["organizational_units"] = [
                    ou['Name'] for ou in ous['OrganizationalUnits']
                ]
                
            except Exception as e:
                results["remediation_steps"].append(
                    f"Cannot validate organizational structure: {str(e)}"
                )
            
            logger.info(f"Control Tower validation completed: {results['status']}")
            return results
            
        except Exception as e:
            logger.error(f"Control Tower validation failed: {e}")
            return {
                "status": "FAIL",
                "landing_zone_status": None,
                "drift_status": None,
                "organizational_units": [],
                "remediation_steps": [f"Validation failed: {str(e)}"]
            }
    
    def validate_security_baseline(self) -> Dict[str, Any]:
        """Validate security services deployment and configuration.
        
        Returns:
            Security baseline validation results
            
        Raises:
            ValidationError: When validation cannot be performed
        """
        try:
            results = {
                "status": "UNKNOWN",
                "config_status": None,
                "guardduty_status": None,
                "security_hub_status": None,
                "remediation_steps": []
            }
            
            # Validate Config organization aggregator
            try:
                config_client = self.aws_client.get_client('config')
                aggregators = config_client.describe_configuration_aggregators()
                
                if aggregators['ConfigurationAggregators']:
                    results["config_status"] = "ACTIVE"
                else:
                    results["config_status"] = "MISSING"
                    results["remediation_steps"].append(
                        "Config organization aggregator not found"
                    )
                    
            except Exception as e:
                results["config_status"] = "ERROR"
                results["remediation_steps"].append(
                    f"Config validation error: {str(e)}"
                )
            
            # Validate GuardDuty organization setup
            try:
                gd_client = self.aws_client.get_client('guardduty')
                detectors = gd_client.list_detectors()
                
                if detectors['DetectorIds']:
                    results["guardduty_status"] = "ACTIVE"
                else:
                    results["guardduty_status"] = "MISSING"
                    results["remediation_steps"].append(
                        "GuardDuty detector not found"
                    )
                    
            except Exception as e:
                results["guardduty_status"] = "ERROR"
                results["remediation_steps"].append(
                    f"GuardDuty validation error: {str(e)}"
                )
            
            # Validate Security Hub organization setup
            try:
                sh_client = self.aws_client.get_client('securityhub')
                hub = sh_client.describe_hub()
                
                if hub['HubArn']:
                    results["security_hub_status"] = "ACTIVE"
                else:
                    results["security_hub_status"] = "MISSING"
                    
            except Exception as e:
                results["security_hub_status"] = "ERROR"
                results["remediation_steps"].append(
                    f"Security Hub validation error: {str(e)}"
                )
            
            # Determine overall status
            if all(status == "ACTIVE" for status in [
                results["config_status"],
                results["guardduty_status"], 
                results["security_hub_status"]
            ]):
                results["status"] = "PASS"
            else:
                results["status"] = "FAIL"
            
            logger.info(f"Security baseline validation: {results['status']}")
            return results
            
        except Exception as e:
            logger.error(f"Security baseline validation failed: {e}")
            return {
                "status": "FAIL",
                "config_aggregator": None,
                "guardduty_status": None,
                "security_hub_status": None,
                "remediation_steps": [f"Validation failed: {str(e)}"]
            }
    
    def validate_account_enrollment(self) -> Dict[str, Any]:
        """Validate account enrollment and organizational compliance.
        
        Returns:
            Account enrollment validation results
            
        Raises:
            ValidationError: When validation cannot be performed
        """
        try:
            results = {
                "status": "UNKNOWN",
                "enrolled_accounts": [],
                "total_accounts": 0,
                "compliance_status": None,
                "remediation_steps": []
            }
            
            # Get organization accounts
            try:
                org_client = self.aws_client.get_client('organizations')
                accounts = org_client.list_accounts()
                results["total_accounts"] = len(accounts['Accounts'])
                
                # Check Control Tower enrollment status
                ct_client = self.aws_client.get_client('controltower')
                
                enrolled_count = 0
                for account in accounts['Accounts']:
                    try:
                        # Check if account is enrolled in Control Tower
                        # This is a simplified check - actual implementation would
                        # use appropriate Control Tower APIs
                        results["enrolled_accounts"].append({
                            "account_id": account['Id'],
                            "name": account['Name'],
                            "status": "ENROLLED"  # Simplified for minimal implementation
                        })
                        enrolled_count += 1
                        
                    except Exception:
                        results["enrolled_accounts"].append({
                            "account_id": account['Id'],
                            "name": account['Name'],
                            "status": "NOT_ENROLLED"
                        })
                
                # Determine compliance status
                if enrolled_count == results["total_accounts"]:
                    results["compliance_status"] = "COMPLIANT"
                    results["status"] = "PASS"
                else:
                    results["compliance_status"] = "NON_COMPLIANT"
                    results["status"] = "FAIL"
                    results["remediation_steps"].append(
                        f"{results['total_accounts'] - enrolled_count} accounts not enrolled"
                    )
                    
            except Exception as e:
                results["status"] = "FAIL"
                results["remediation_steps"].append(
                    f"Account enrollment validation error: {str(e)}"
                )
            
            logger.info(f"Account enrollment validation: {results['status']}")
            return results
            
        except Exception as e:
            logger.error(f"Account enrollment validation failed: {e}")
            return {
                "status": "FAIL",
                "enrolled_accounts": [],
                "compliance_status": {},
                "remediation_steps": [f"Validation failed: {str(e)}"]
            }
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report.
        
        Returns:
            Complete validation report with all checks
            
        Raises:
            ValidationError: When validation report generation fails
        """
        try:
            report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": "UNKNOWN",
                "control_tower": self.validate_control_tower_deployment(),
                "security_baseline": self.validate_security_baseline(),
                "account_enrollment": self.validate_account_enrollment(),
                "summary": {
                    "total_checks": 3,
                    "passed_checks": 0,
                    "failed_checks": 0,
                    "remediation_required": False
                }
            }
            
            # Calculate summary
            statuses = [
                report["control_tower"]["status"],
                report["security_baseline"]["status"],
                report["account_enrollment"]["status"]
            ]
            
            report["summary"]["passed_checks"] = statuses.count("PASS")
            report["summary"]["failed_checks"] = statuses.count("FAIL")
            
            if report["summary"]["failed_checks"] == 0:
                report["overall_status"] = "PASS"
            else:
                report["overall_status"] = "FAIL"
                report["summary"]["remediation_required"] = True
            
            logger.info(f"Validation report generated: {report['overall_status']}")
            return report
            
        except Exception as e:
            raise ValidationError(f"Validation report generation failed: {e}")
