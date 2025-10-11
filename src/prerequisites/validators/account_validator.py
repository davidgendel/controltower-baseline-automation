"""Account structure validator for Control Tower prerequisites.

This module validates that required Log Archive and Audit accounts exist
for Control Tower deployment and provides remediation steps when accounts
are missing.
"""

from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

from ...core.aws_client import AWSClientManager
from ...core.validator import BaseValidator, ValidationResult, ValidationStatus
from ..accounts import AccountManager


class AccountStructureValidator(BaseValidator):
    """Validates account structure for Control Tower deployment."""
    
    @property
    def name(self) -> str:
        """Validator name."""
        return "Account Structure"
    
    def __init__(self, aws_client: AWSClientManager) -> None:
        """Initialize validator.
        
        Args:
            aws_client: Configured AWS client manager
        """
        super().__init__(aws_client)
        self.account_manager = AccountManager(aws_client)
        
    def validate(self) -> ValidationResult:
        """Validate account structure requirements.
        
        Returns:
            ValidationResult with account structure status
        """
        try:
            # Check if required accounts exist
            log_archive_account = self._check_log_archive_account()
            audit_account = self._check_audit_account()
            
            issues = []
            if not log_archive_account:
                issues.append("Log Archive account not found")
            if not audit_account:
                issues.append("Audit account not found")
                
            if issues:
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.FAILED,
                    message="Required accounts missing",
                    details={"missing_accounts": issues},
                    remediation_steps=self._get_remediation_steps(issues)
                )
                
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.PASSED,
                message="Account structure validated successfully",
                details={
                    "log_archive_account": log_archive_account,
                    "audit_account": audit_account
                }
            )
            
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message=f"Account validation failed: {str(e)}",
                details={"error": str(e)}
            )
            
    def _check_log_archive_account(self) -> Optional[Dict[str, Any]]:
        """Check if Log Archive account exists."""
        # Look for account with "log" or "archive" in name
        accounts = self.account_manager.list_accounts()
        for account in accounts:
            name = account.get('Name', '').lower()
            if 'log' in name and 'archive' in name:
                return account
        return None
        
    def _check_audit_account(self) -> Optional[Dict[str, Any]]:
        """Check if Audit account exists."""
        # Look for account with "audit" in name
        accounts = self.account_manager.list_accounts()
        for account in accounts:
            name = account.get('Name', '').lower()
            if 'audit' in name:
                return account
        return None
        
    def _get_remediation_steps(self, issues: List[str]) -> List[str]:
        """Get remediation steps for account issues."""
        steps = []
        
        if "Log Archive account not found" in issues:
            steps.extend([
                "Create Log Archive account:",
                "  1. Use AccountManager.create_account('Log Archive', 'log-archive@yourdomain.com')",
                "  2. Move account to Security OU after creation"
            ])
            
        if "Audit account not found" in issues:
            steps.extend([
                "Create Audit account:",
                "  1. Use AccountManager.create_account('Audit', 'audit@yourdomain.com')",
                "  2. Move account to Security OU after creation"
            ])
            
        return steps
