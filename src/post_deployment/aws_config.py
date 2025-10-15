"""AWS Config organization-wide setup and aggregation management.

This module handles Config delegated administrator setup, organization
aggregator configuration, and Config rules deployment across the organization.
"""

from typing import Dict, List, Optional, Any
import logging
from botocore.exceptions import ClientError

from src.core.aws_client import AWSClientManager
from src.core.config import Configuration


logger = logging.getLogger(__name__)


class ConfigOrganizationError(Exception):
    """Raised when Config organization setup fails."""
    pass


class ConfigOrganizationManager:
    """Manages AWS Config organization-wide setup and aggregation."""
    
    def __init__(self, config: Configuration, aws_client: AWSClientManager):
        """Initialize Config organization manager.
        
        Args:
            config: Configuration instance
            aws_client: AWS client manager instance
        """
        self.config = config
        self.aws_client = aws_client
        
    def enable_delegated_administrator(self, account_id: str) -> bool:
        """Enable delegated administrator for AWS Config organization setup.
        
        Args:
            account_id: AWS account ID to designate as delegated administrator
            
        Returns:
            True if delegation successful, False otherwise
            
        Raises:
            ConfigOrganizationError: When delegation setup fails
        """
        try:
            orgs_client = self.aws_client.get_client('organizations')
            
            # Enable service access for Config
            orgs_client.enable_aws_service_access(
                ServicePrincipal='config.amazonaws.com'
            )
            orgs_client.enable_aws_service_access(
                ServicePrincipal='config-multiaccountsetup.amazonaws.com'
            )
            
            # Register delegated administrator
            orgs_client.register_delegated_administrator(
                AccountId=account_id,
                ServicePrincipal='config.amazonaws.com'
            )
            orgs_client.register_delegated_administrator(
                AccountId=account_id,
                ServicePrincipal='config-multiaccountsetup.amazonaws.com'
            )
            
            logger.info(f"Config delegated administrator enabled for {account_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccountAlreadyRegisteredException':
                logger.info(f"Config delegation already exists for {account_id}")
                return True
            raise ConfigOrganizationError(f"Failed to enable Config delegation: {e}")
    
    def create_organization_aggregator(self) -> Dict[str, Any]:
        """Create organization aggregator with proper IAM role setup.
        
        Returns:
            Dict containing aggregator configuration details
            
        Raises:
            ConfigOrganizationError: When aggregator creation fails
        """
        try:
            config_client = self.aws_client.get_client('config')
            
            aggregator_name = 'OrganizationConfigAggregator'
            
            # Create organization aggregator
            response = config_client.put_configuration_aggregator(
                ConfigurationAggregatorName=aggregator_name,
                OrganizationAggregationSource={
                    'RoleArn': f'arn:aws:iam::{self.aws_client.account_id}:role/aws-controltower-ConfigAggregatorRoleForOrganizations',
                    'AwsRegions': self.config.get_governed_regions(),
                    'AllAwsRegions': False
                }
            )
            
            logger.info(f"Organization aggregator created: {aggregator_name}")
            return response['ConfigurationAggregator']
            
        except ClientError as e:
            raise ConfigOrganizationError(f"Failed to create aggregator: {e}")
    
    def validate_config_setup(self) -> Dict[str, bool]:
        """Validate Config setup across organization.
        
        Returns:
            Dict with validation results for each component
        """
        results = {
            'delegated_admin': False,
            'aggregator': False,
            'service_access': False
        }
        
        try:
            orgs_client = self.aws_client.get_client('organizations')
            config_client = self.aws_client.get_client('config')
            
            # Check service access
            services = orgs_client.list_aws_service_access_for_organization()
            enabled_services = [s['ServicePrincipal'] for s in services['EnabledServicePrincipals']]
            results['service_access'] = 'config.amazonaws.com' in enabled_services
            
            # Check delegated administrator
            admins = orgs_client.list_delegated_administrators(
                ServicePrincipal='config.amazonaws.com'
            )
            results['delegated_admin'] = len(admins['DelegatedAdministrators']) > 0
            
            # Check aggregator
            aggregators = config_client.describe_configuration_aggregators()
            results['aggregator'] = len(aggregators['ConfigurationAggregators']) > 0
            
        except ClientError as e:
            logger.error(f"Config validation failed: {e}")
            
        return results
