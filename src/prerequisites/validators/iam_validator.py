"""IAM roles validator for Control Tower prerequisites.

This module validates that required IAM roles exist for Control Tower
deployment and provides information about roles that will be created
automatically during Control Tower setup.
"""

from typing import List
from ...core.aws_client import AWSClientManager
from ...core.validator import BaseValidator, ValidationResult, ValidationStatus
from ..iam_roles import IAMRolesManager


class IAMRolesValidator(BaseValidator):
    """Validates IAM roles for Control Tower deployment."""
    
    @property
    def name(self) -> str:
        """Validator name."""
        return "IAM Roles"
    
    def __init__(self, aws_client: AWSClientManager) -> None:
        """Initialize validator.
        
        Args:
            aws_client: Configured AWS client manager
        """
        super().__init__(aws_client)
        self.iam_manager = IAMRolesManager(aws_client)
        
    def validate(self) -> ValidationResult:
        """Validate IAM roles requirements.
        
        Returns:
            ValidationResult with IAM roles status
        """
        try:
            summary = self.iam_manager.get_roles_summary()
            
            if summary['missing_roles']:
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.WARNING,
                    message="Control Tower roles will be created automatically",
                    details={
                        "missing_roles": summary['missing_roles'],
                        "existing_roles": summary['existing_roles'],
                        "total_roles": summary['total_roles']
                    },
                    remediation_steps=self._get_remediation_steps(summary['missing_roles'])
                )
                
            # Check trust policies for existing roles
            trust_issues = []
            for role_name, details in summary['role_details'].items():
                if details['exists'] and not details['trust_policy_valid']:
                    trust_issues.append(role_name)
                    
            if trust_issues:
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.WARNING,
                    message="Some roles have invalid trust policies",
                    details={
                        "roles_with_trust_issues": trust_issues,
                        "summary": summary
                    },
                    remediation_steps=[
                        "Review trust policies for roles with issues",
                        "Ensure roles trust appropriate AWS services",
                        "Control Tower will recreate roles if needed during setup"
                    ]
                )
                
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.PASSED,
                message="IAM roles validation completed successfully",
                details=summary
            )
            
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message=f"IAM roles validation failed: {str(e)}",
                details={"error": str(e)}
            )
            
    def _get_remediation_steps(self, missing_roles: List[str]) -> List[str]:
        """Get remediation steps for missing roles."""
        steps = [
            "Control Tower will create required roles automatically during setup:",
        ]
        
        for role in missing_roles:
            role_info = self.iam_manager.CONTROL_TOWER_ROLES.get(role, {})
            description = role_info.get('description', 'Control Tower role')
            steps.append(f"  - {role}: {description}")
            
        steps.extend([
            "",
            "No manual action required - roles are created during Control Tower deployment",
            "Ensure your account has permissions to create IAM roles"
        ])
        
        return steps
