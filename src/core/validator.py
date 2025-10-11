"""Prerequisites validation framework for AWS Control Tower.

This module provides a comprehensive validation framework for checking
all AWS Control Tower prerequisites including Organizations setup,
IAM permissions, and account requirements.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError

from .aws_client import AWSClientManager


class ValidationStatus(Enum):
    """Validation result status."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


@dataclass
class ValidationResult:
    """Result of a validation check."""

    validator_name: str
    status: ValidationStatus
    message: str
    remediation_steps: Optional[List[str]] = None
    details: Optional[Dict[str, Any]] = None


class BaseValidator(ABC):
    """Base class for all validators."""

    def __init__(self, aws_client: AWSClientManager) -> None:
        """Initialize validator with AWS client manager.

        Args:
            aws_client: Configured AWS client manager
        """
        self.aws_client = aws_client

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Perform validation check.

        Returns:
            ValidationResult with status and details
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get validator name."""
        pass


class CredentialsValidator(BaseValidator):
    """Validates AWS credentials and permissions."""

    @property
    def name(self) -> str:
        """Get validator name."""
        return "AWS Credentials"

    def validate(self) -> ValidationResult:
        """Validate AWS credentials are working.

        Returns:
            ValidationResult indicating credential status
        """
        try:
            account_id = self.aws_client.get_account_id()
            region = self.aws_client.get_current_region()

            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.PASSED,
                message=f"AWS credentials valid for account {account_id} in region {region}",
                details={"account_id": account_id, "region": region},
            )

        except NoCredentialsError as e:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message=str(e),
                remediation_steps=[
                    "Configure AWS credentials using one of these methods:",
                    "1. AWS CLI: Run 'aws configure'",
                    "2. Environment variables: Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY",
                    "3. IAM roles: Attach appropriate IAM role to EC2 instance",
                    "4. AWS profiles: Set AWS_PROFILE environment variable",
                ],
            )
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message=f"Credential validation failed: {str(e)}",
                remediation_steps=[
                    "Check AWS credential configuration",
                    "Verify IAM permissions for STS GetCallerIdentity",
                ],
            )


class OrganizationsValidator(BaseValidator):
    """Validates AWS Organizations prerequisites."""

    @property
    def name(self) -> str:
        """Get validator name."""
        return "AWS Organizations"

    def validate(self) -> ValidationResult:
        """Validate AWS Organizations setup.

        Returns:
            ValidationResult indicating Organizations status
        """
        try:
            org_client = self.aws_client.get_client(
                "organizations", self.aws_client.get_current_region()
            )

            # Check if organization exists
            try:
                org_response = org_client.describe_organization()
                organization = org_response["Organization"]
            except ClientError as e:
                if (
                    e.response["Error"]["Code"]
                    == "AWSOrganizationsNotInUseException"
                ):
                    return ValidationResult(
                        validator_name=self.name,
                        status=ValidationStatus.FAILED,
                        message="AWS Organizations is not enabled for this account",
                        remediation_steps=[
                            "Enable AWS Organizations:",
                            "1. Go to AWS Organizations console",
                            "2. Click 'Create organization'",
                            "3. Choose 'Enable all features' (required for Control Tower)",
                        ],
                    )
                raise

            # Check if all features are enabled
            if organization["FeatureSet"] != "ALL":
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.FAILED,
                    message="AWS Organizations does not have all features enabled",
                    remediation_steps=[
                        "Enable all features in AWS Organizations:",
                        "1. Go to AWS Organizations console",
                        "2. Navigate to Settings",
                        "3. Click 'Enable all features'",
                        "4. Confirm the change (this cannot be undone)",
                    ],
                )

            # Check if this is the management account
            account_id = self.aws_client.get_account_id()
            if organization["MasterAccountId"] != account_id:
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.FAILED,
                    message="Control Tower must be deployed from the management account",
                    remediation_steps=[
                        f"Switch to the management account: {organization['MasterAccountId']}",
                        "Control Tower can only be deployed from the organization's management account",
                    ],
                )

            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.PASSED,
                message="AWS Organizations is properly configured with all features enabled",
                details={
                    "organization_id": organization["Id"],
                    "management_account_id": organization["MasterAccountId"],
                    "feature_set": organization["FeatureSet"],
                },
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.FAILED,
                    message="Insufficient permissions to access AWS Organizations",
                    remediation_steps=[
                        "Ensure the following IAM permissions are granted:",
                        "- organizations:DescribeOrganization",
                        "- organizations:ListAccounts",
                        "- organizations:ListRoots",
                    ],
                )
            else:
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.FAILED,
                    message=f"Organizations validation failed: {str(e)}",
                    remediation_steps=[
                        "Check AWS Organizations service status",
                        "Verify IAM permissions for Organizations access",
                    ],
                )


class ControlTowerValidator(BaseValidator):
    """Validates existing Control Tower deployment status."""

    @property
    def name(self) -> str:
        """Get validator name."""
        return "Control Tower Status"

    def validate(self) -> ValidationResult:
        """Check if Control Tower is already deployed.

        Returns:
            ValidationResult indicating Control Tower status
        """
        try:
            ct_client = self.aws_client.get_client(
                "controltower", self.aws_client.get_current_region()
            )

            # Check for existing landing zone
            try:
                response = ct_client.list_landing_zones()
                landing_zones = response.get("landingZones", [])

                if landing_zones:
                    # Control Tower is already deployed
                    lz = landing_zones[0]  # Should only be one
                    return ValidationResult(
                        validator_name=self.name,
                        status=ValidationStatus.WARNING,
                        message="Control Tower landing zone already exists",
                        details={
                            "landing_zone_arn": lz.get("arn"),
                            "status": lz.get("status"),
                        },
                        remediation_steps=[
                            "Control Tower is already deployed in this organization",
                            "If you need to modify the configuration, use the Control Tower console",
                            "To redeploy, you must first delete the existing landing zone",
                        ],
                    )
                else:
                    return ValidationResult(
                        validator_name=self.name,
                        status=ValidationStatus.PASSED,
                        message="No existing Control Tower deployment found - ready for new deployment",
                    )

            except ClientError as e:
                if e.response["Error"]["Code"] == "AccessDenied":
                    return ValidationResult(
                        validator_name=self.name,
                        status=ValidationStatus.FAILED,
                        message="Insufficient permissions to check Control Tower status",
                        remediation_steps=[
                            "Ensure the following IAM permissions are granted:",
                            "- controltower:ListLandingZones",
                            "- controltower:GetLandingZone",
                        ],
                    )
                else:
                    # Assume no Control Tower if we can't check
                    return ValidationResult(
                        validator_name=self.name,
                        status=ValidationStatus.PASSED,
                        message="Control Tower service accessible - ready for deployment",
                    )

        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message=f"Control Tower validation failed: {str(e)}",
                remediation_steps=[
                    "Check Control Tower service availability in your region",
                    "Verify IAM permissions for Control Tower access",
                ],
            )


class OrganizationsStructureValidator(BaseValidator):
    """Validates AWS Organizations structure for Control Tower."""
    
    @property
    def name(self) -> str:
        """Get validator name."""
        return "Organizations Structure"
        
    def validate(self) -> ValidationResult:
        """Validate Organizations structure for Control Tower.
        
        Returns:
            ValidationResult indicating Organizations structure status
        """
        try:
            from ..prerequisites.organizations import OrganizationsManager
            
            org_manager = OrganizationsManager(self.aws_client)
            validation_results = org_manager.validate_organization_structure()
            
            if validation_results['valid']:
                details = {
                    'organization_id': validation_results['organization_info'].get('Id'),
                    'feature_set': validation_results['organization_info'].get('FeatureSet'),
                    'root_id': validation_results['root_id'],
                    'security_ou_id': validation_results.get('security_ou', {}).get('Id'),
                    'sandbox_ou_id': validation_results.get('sandbox_ou', {}).get('Id')
                }
                
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.PASSED,
                    message="Organizations structure is ready for Control Tower",
                    details=details
                )
            else:
                remediation_steps = [
                    "Fix the following Organizations issues:"
                ]
                
                for issue in validation_results['issues']:
                    if "all features enabled" in issue:
                        remediation_steps.extend([
                            "1. Enable all features in AWS Organizations:",
                            "   - Go to AWS Organizations console",
                            "   - Navigate to Settings",
                            "   - Click 'Enable all features'",
                            "   - Confirm the change (cannot be undone)"
                        ])
                    elif "Security OU not found" in issue:
                        remediation_steps.append(
                            "2. Create Security OU under root organization"
                        )
                    elif "Sandbox OU not found" in issue:
                        remediation_steps.append(
                            "3. Create Sandbox OU under root organization"
                        )
                        
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.FAILED,
                    message=f"Organizations structure issues: {', '.join(validation_results['issues'])}",
                    remediation_steps=remediation_steps,
                    details=validation_results
                )
                
        except Exception as e:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message=f"Organizations validation failed: {str(e)}",
                remediation_steps=[
                    "Check AWS Organizations service status",
                    "Verify IAM permissions for Organizations access",
                    "Ensure you're running from the management account"
                ]
            )


class PrerequisitesValidator:
    """Main validator orchestrator for all prerequisites."""

    def __init__(self, aws_client: AWSClientManager) -> None:
        """Initialize prerequisites validator.

        Args:
            aws_client: Configured AWS client manager
        """
        self.aws_client = aws_client
        # Import here to avoid circular imports
        from ..prerequisites.validators.account_validator import AccountStructureValidator
        from ..prerequisites.validators.iam_validator import IAMRolesValidator
        
        self.validators = [
            CredentialsValidator(aws_client),
            OrganizationsValidator(aws_client),
            OrganizationsStructureValidator(aws_client),
            AccountStructureValidator(aws_client),
            IAMRolesValidator(aws_client),
            ControlTowerValidator(aws_client),
        ]

    def validate_all(self) -> List[ValidationResult]:
        """Run all validation checks.

        Returns:
            List of ValidationResult objects
        """
        results = []

        for validator in self.validators:
            try:
                result = validator.validate()
                results.append(result)

                # Stop on critical failures
                if (
                    result.status == ValidationStatus.FAILED
                    and validator.name
                    in ["AWS Credentials", "AWS Organizations"]
                ):
                    break

            except Exception as e:
                results.append(
                    ValidationResult(
                        validator_name=validator.name,
                        status=ValidationStatus.FAILED,
                        message=f"Validation error: {str(e)}",
                        remediation_steps=[
                            "Check validator implementation",
                            "Verify AWS service availability",
                        ],
                    )
                )

        return results

    def is_ready_for_deployment(self, results: List[ValidationResult]) -> bool:
        """Check if all prerequisites are met for deployment.

        Args:
            results: List of validation results

        Returns:
            True if ready for deployment, False otherwise
        """
        for result in results:
            if result.status == ValidationStatus.FAILED:
                return False
        return True
