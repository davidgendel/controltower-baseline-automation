"""Unit tests for AWS Config organization management."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.post_deployment.aws_config import ConfigOrganizationManager, ConfigOrganizationError
from src.core.config import Configuration
from src.core.aws_client import AWSClientManager


@pytest.fixture
def mock_config():
    config = Mock(spec=Configuration)
    config.get_governed_regions.return_value = ['us-east-1', 'us-west-2']
    return config


@pytest.fixture
def mock_aws_client():
    client = Mock(spec=AWSClientManager)
    client.account_id = '123456789012'
    return client


@pytest.fixture
def config_manager(mock_config, mock_aws_client):
    return ConfigOrganizationManager(mock_config, mock_aws_client)


class TestConfigOrganizationManager:
    
    def test_enable_delegated_administrator_success(self, config_manager, mock_aws_client):
        """Test successful delegated administrator enablement."""
        mock_orgs = Mock()
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = config_manager.enable_delegated_administrator('123456789012')
        
        assert result is True
        mock_orgs.enable_aws_service_access.assert_any_call(
            ServicePrincipal='config.amazonaws.com'
        )
        mock_orgs.enable_aws_service_access.assert_any_call(
            ServicePrincipal='config-multiaccountsetup.amazonaws.com'
        )
        mock_orgs.register_delegated_administrator.assert_any_call(
            AccountId='123456789012',
            ServicePrincipal='config.amazonaws.com'
        )
    
    def test_enable_delegated_administrator_already_exists(self, config_manager, mock_aws_client):
        """Test delegated administrator already exists."""
        mock_orgs = Mock()
        mock_orgs.register_delegated_administrator.side_effect = ClientError(
            {'Error': {'Code': 'AccountAlreadyRegisteredException'}}, 'RegisterDelegatedAdministrator'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = config_manager.enable_delegated_administrator('123456789012')
        
        assert result is True
    
    def test_enable_delegated_administrator_failure(self, config_manager, mock_aws_client):
        """Test delegated administrator enablement failure."""
        mock_orgs = Mock()
        mock_orgs.register_delegated_administrator.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'RegisterDelegatedAdministrator'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        with pytest.raises(ConfigOrganizationError):
            config_manager.enable_delegated_administrator('123456789012')
    
    def test_create_organization_aggregator_success(self, config_manager, mock_aws_client):
        """Test successful organization aggregator creation."""
        mock_config = Mock()
        mock_config.put_configuration_aggregator.return_value = {
            'ConfigurationAggregator': {'ConfigurationAggregatorName': 'OrganizationConfigAggregator'}
        }
        mock_aws_client.get_client.return_value = mock_config
        
        result = config_manager.create_organization_aggregator()
        
        assert result['ConfigurationAggregatorName'] == 'OrganizationConfigAggregator'
        mock_config.put_configuration_aggregator.assert_called_once()
    
    def test_create_organization_aggregator_failure(self, config_manager, mock_aws_client):
        """Test organization aggregator creation failure."""
        mock_config = Mock()
        mock_config.put_configuration_aggregator.side_effect = ClientError(
            {'Error': {'Code': 'InsufficientPermissionsException'}}, 'PutConfigurationAggregator'
        )
        mock_aws_client.get_client.return_value = mock_config
        
        with pytest.raises(ConfigOrganizationError):
            config_manager.create_organization_aggregator()
    
    def test_validate_config_setup_success(self, config_manager, mock_aws_client):
        """Test successful Config setup validation."""
        mock_orgs = Mock()
        mock_orgs.list_aws_service_access_for_organization.return_value = {
            'EnabledServicePrincipals': [{'ServicePrincipal': 'config.amazonaws.com'}]
        }
        mock_orgs.list_delegated_administrators.return_value = {
            'DelegatedAdministrators': [{'Id': '123456789012'}]
        }
        
        mock_config = Mock()
        mock_config.describe_configuration_aggregators.return_value = {
            'ConfigurationAggregators': [{'ConfigurationAggregatorName': 'test'}]
        }
        
        mock_aws_client.get_client.side_effect = lambda service: mock_orgs if service == 'organizations' else mock_config
        
        result = config_manager.validate_config_setup()
        
        assert result['service_access'] is True
        assert result['delegated_admin'] is True
        assert result['aggregator'] is True
    
    def test_validate_config_setup_failure(self, config_manager, mock_aws_client):
        """Test Config setup validation with failures."""
        mock_orgs = Mock()
        mock_orgs.list_aws_service_access_for_organization.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'ListAWSServiceAccessForOrganization'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = config_manager.validate_config_setup()
        
        assert result['service_access'] is False
        assert result['delegated_admin'] is False
        assert result['aggregator'] is False
