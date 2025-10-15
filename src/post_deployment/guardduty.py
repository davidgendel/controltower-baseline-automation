"""GuardDuty organization-wide setup and centralized management.

This module handles GuardDuty delegated administrator setup, organization-wide
enablement, and feature configuration across the organization.
"""

from typing import Dict, List, Optional, Any
import logging
from botocore.exceptions import ClientError

from src.core.aws_client import AWSClientManager
from src.core.config import Configuration


logger = logging.getLogger(__name__)


class GuardDutyOrganizationError(Exception):
    """Raised when GuardDuty organization setup fails."""
    pass


class GuardDutyOrganizationManager:
    """Manages GuardDuty organization-wide setup and centralized management."""
    
    def __init__(self, config: Configuration, aws_client: AWSClientManager):
        """Initialize GuardDuty organization manager.
        
        Args:
            config: Configuration instance
            aws_client: AWS client manager instance
        """
        self.config = config
        self.aws_client = aws_client
        
    def enable_delegated_administrator(self, account_id: str) -> bool:
        """Enable delegated administrator for GuardDuty organization setup.
        
        Args:
            account_id: AWS account ID to designate as delegated administrator
            
        Returns:
            True if delegation successful, False otherwise
            
        Raises:
            GuardDutyOrganizationError: When delegation setup fails
        """
        try:
            orgs_client = self.aws_client.get_client('organizations')
            
            # Enable service access for GuardDuty
            orgs_client.enable_aws_service_access(
                ServicePrincipal='guardduty.amazonaws.com'
            )
            
            # Register delegated administrator
            orgs_client.register_delegated_administrator(
                AccountId=account_id,
                ServicePrincipal='guardduty.amazonaws.com'
            )
            
            logger.info(f"GuardDuty delegated administrator enabled for {account_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccountAlreadyRegisteredException':
                logger.info(f"GuardDuty delegation already exists for {account_id}")
                return True
            raise GuardDutyOrganizationError(f"Failed to enable GuardDuty delegation: {e}")
    
    def enable_organization_guardduty(self, auto_enable: bool = True) -> Dict[str, Any]:
        """Enable GuardDuty organization-wide with auto-enable configuration.
        
        Args:
            auto_enable: Whether to auto-enable GuardDuty for new accounts
            
        Returns:
            Dict containing organization configuration details
            
        Raises:
            GuardDutyOrganizationError: When organization setup fails
        """
        try:
            guardduty_client = self.aws_client.get_client('guardduty')
            
            # Get or create detector
            detectors = guardduty_client.list_detectors()
            if not detectors['DetectorIds']:
                detector_response = guardduty_client.create_detector(Enable=True)
                detector_id = detector_response['DetectorId']
            else:
                detector_id = detectors['DetectorIds'][0]
            
            # Update organization configuration
            guardduty_client.update_organization_configuration(
                DetectorId=detector_id,
                AutoEnable=auto_enable,
                DataSources={
                    'S3Logs': {'AutoEnable': auto_enable},
                    'Kubernetes': {'AuditLogs': {'AutoEnable': auto_enable}},
                    'MalwareProtection': {'ScanEc2InstanceWithFindings': {'EbsVolumes': {'AutoEnable': auto_enable}}}
                }
            )
            
            logger.info(f"GuardDuty organization configuration updated, auto-enable: {auto_enable}")
            return {'detector_id': detector_id, 'auto_enable': auto_enable}
            
        except ClientError as e:
            raise GuardDutyOrganizationError(f"Failed to configure GuardDuty organization: {e}")
    
    def set_finding_frequency(self, frequency: str = 'SIX_HOURS') -> bool:
        """Set finding publishing frequency for organization.
        
        Args:
            frequency: Finding frequency (FIFTEEN_MINUTES, ONE_HOUR, SIX_HOURS)
            
        Returns:
            True if frequency set successfully
            
        Raises:
            GuardDutyOrganizationError: When frequency setting fails
        """
        try:
            guardduty_client = self.aws_client.get_client('guardduty')
            
            # Get detector ID
            detectors = guardduty_client.list_detectors()
            if not detectors['DetectorIds']:
                raise GuardDutyOrganizationError("No GuardDuty detector found")
            
            detector_id = detectors['DetectorIds'][0]
            
            # Update finding frequency
            guardduty_client.update_detector(
                DetectorId=detector_id,
                FindingPublishingFrequency=frequency
            )
            
            logger.info(f"GuardDuty finding frequency set to {frequency}")
            return True
            
        except ClientError as e:
            raise GuardDutyOrganizationError(f"Failed to set finding frequency: {e}")
    
    def validate_guardduty_setup(self) -> Dict[str, bool]:
        """Validate GuardDuty setup across organization.
        
        Returns:
            Dict with validation results for each component
        """
        results = {
            'delegated_admin': False,
            'detector_enabled': False,
            'organization_config': False,
            'service_access': False
        }
        
        try:
            orgs_client = self.aws_client.get_client('organizations')
            guardduty_client = self.aws_client.get_client('guardduty')
            
            # Check service access
            services = orgs_client.list_aws_service_access_for_organization()
            enabled_services = [s['ServicePrincipal'] for s in services['EnabledServicePrincipals']]
            results['service_access'] = 'guardduty.amazonaws.com' in enabled_services
            
            # Check delegated administrator
            admins = orgs_client.list_delegated_administrators(
                ServicePrincipal='guardduty.amazonaws.com'
            )
            results['delegated_admin'] = len(admins['DelegatedAdministrators']) > 0
            
            # Check detector
            detectors = guardduty_client.list_detectors()
            results['detector_enabled'] = len(detectors['DetectorIds']) > 0
            
            # Check organization configuration
            if detectors['DetectorIds']:
                org_config = guardduty_client.describe_organization_configuration(
                    DetectorId=detectors['DetectorIds'][0]
                )
                results['organization_config'] = org_config.get('AutoEnable', False)
            
        except ClientError as e:
            logger.error(f"GuardDuty validation failed: {e}")
            
        return results
