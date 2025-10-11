"""Security Hub organization-wide setup and centralized management.

This module handles Security Hub delegated administrator setup, organization-wide
enablement, and foundational security standards configuration.
"""

from typing import Dict, List, Optional, Any
import logging
from botocore.exceptions import ClientError

from ..core.aws_client import AWSClientManager
from ..core.config import Configuration


logger = logging.getLogger(__name__)


class SecurityHubOrganizationError(Exception):
    """Raised when Security Hub organization setup fails."""
    pass


class SecurityHubOrganizationManager:
    """Manages Security Hub organization-wide setup and centralized management."""
    
    def __init__(self, config: Configuration, aws_client: AWSClientManager):
        """Initialize Security Hub organization manager.
        
        Args:
            config: Configuration instance
            aws_client: AWS client manager instance
        """
        self.config = config
        self.aws_client = aws_client
        
    def enable_delegated_administrator(self, account_id: str) -> bool:
        """Enable delegated administrator for Security Hub organization setup.
        
        Args:
            account_id: AWS account ID to designate as delegated administrator
            
        Returns:
            True if delegation successful, False otherwise
            
        Raises:
            SecurityHubOrganizationError: When delegation setup fails
        """
        try:
            orgs_client = self.aws_client.get_client('organizations')
            
            # Enable service access for Security Hub
            orgs_client.enable_aws_service_access(
                ServicePrincipal='securityhub.amazonaws.com'
            )
            
            # Register delegated administrator
            orgs_client.register_delegated_administrator(
                AccountId=account_id,
                ServicePrincipal='securityhub.amazonaws.com'
            )
            
            logger.info(f"Security Hub delegated administrator enabled for {account_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccountAlreadyRegisteredException':
                logger.info(f"Security Hub delegation already exists for {account_id}")
                return True
            raise SecurityHubOrganizationError(f"Failed to enable Security Hub delegation: {e}")
    
    def enable_organization_security_hub(self, auto_enable: bool = True) -> Dict[str, Any]:
        """Enable Security Hub organization-wide with auto-enable configuration.
        
        Args:
            auto_enable: Whether to auto-enable Security Hub for new accounts
            
        Returns:
            Dict containing organization configuration details
            
        Raises:
            SecurityHubOrganizationError: When organization setup fails
        """
        try:
            securityhub_client = self.aws_client.get_client('securityhub')
            
            # Enable Security Hub if not already enabled
            try:
                securityhub_client.enable_security_hub()
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceConflictException':
                    raise
            
            # Update organization configuration
            securityhub_client.update_organization_configuration(
                AutoEnable=auto_enable,
                AutoEnableStandards='DEFAULT'
            )
            
            logger.info(f"Security Hub organization configuration updated, auto-enable: {auto_enable}")
            return {'auto_enable': auto_enable, 'auto_enable_standards': 'DEFAULT'}
            
        except ClientError as e:
            raise SecurityHubOrganizationError(f"Failed to configure Security Hub organization: {e}")
    
    def enable_foundational_standards(self) -> List[Dict[str, Any]]:
        """Enable foundational security standards (FSBP, CIS).
        
        Returns:
            List of enabled standards with their details
            
        Raises:
            SecurityHubOrganizationError: When standards enablement fails
        """
        try:
            securityhub_client = self.aws_client.get_client('securityhub')
            
            # Get available standards
            standards = securityhub_client.describe_standards()
            
            enabled_standards = []
            for standard in standards['Standards']:
                standard_arn = standard['StandardsArn']
                
                # Enable foundational standards
                if any(name in standard_arn for name in ['aws-foundational', 'cis-aws-foundations']):
                    try:
                        response = securityhub_client.batch_enable_standards(
                            StandardsSubscriptionRequests=[
                                {'StandardsArn': standard_arn}
                            ]
                        )
                        enabled_standards.extend(response['StandardsSubscriptions'])
                        logger.info(f"Enabled Security Hub standard: {standard['Name']}")
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'ResourceConflictException':
                            logger.warning(f"Failed to enable standard {standard['Name']}: {e}")
            
            return enabled_standards
            
        except ClientError as e:
            raise SecurityHubOrganizationError(f"Failed to enable foundational standards: {e}")
    
    def validate_security_hub_setup(self) -> Dict[str, bool]:
        """Validate Security Hub setup across organization.
        
        Returns:
            Dict with validation results for each component
        """
        results = {
            'delegated_admin': False,
            'security_hub_enabled': False,
            'organization_config': False,
            'standards_enabled': False,
            'service_access': False
        }
        
        try:
            orgs_client = self.aws_client.get_client('organizations')
            securityhub_client = self.aws_client.get_client('securityhub')
            
            # Check service access
            services = orgs_client.list_aws_service_access_for_organization()
            enabled_services = [s['ServicePrincipal'] for s in services['EnabledServicePrincipals']]
            results['service_access'] = 'securityhub.amazonaws.com' in enabled_services
            
            # Check delegated administrator
            admins = orgs_client.list_delegated_administrators(
                ServicePrincipal='securityhub.amazonaws.com'
            )
            results['delegated_admin'] = len(admins['DelegatedAdministrators']) > 0
            
            # Check Security Hub enabled
            try:
                securityhub_client.get_enabled_standards()
                results['security_hub_enabled'] = True
                
                # Check organization configuration
                org_config = securityhub_client.describe_organization_configuration()
                results['organization_config'] = org_config.get('AutoEnable', False)
                
                # Check standards
                standards = securityhub_client.get_enabled_standards()
                results['standards_enabled'] = len(standards['StandardsSubscriptions']) > 0
                
            except ClientError:
                results['security_hub_enabled'] = False
            
        except ClientError as e:
            logger.error(f"Security Hub validation failed: {e}")
            
        return results
