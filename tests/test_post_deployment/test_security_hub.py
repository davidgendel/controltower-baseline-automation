"""Unit tests for Security Hub organization management."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.post_deployment.security_hub import SecurityHubOrganizationManager, SecurityHubOrganizationError
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
def security_hub_manager(mock_config, mock_aws_client):
    return SecurityHubOrganizationManager(mock_config, mock_aws_client)


class TestSecurityHubOrganizationManager:
    
    def test_enable_delegated_administrator_success(self, security_hub_manager, mock_aws_client):
        """Test successful delegated administrator enablement."""
        mock_orgs = Mock()
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = security_hub_manager.enable_delegated_administrator('123456789012')
        
        assert result is True
        mock_orgs.enable_aws_service_access.assert_called_once_with(
            ServicePrincipal='securityhub.amazonaws.com'
        )
        mock_orgs.register_delegated_administrator.assert_called_once_with(
            AccountId='123456789012',
            ServicePrincipal='securityhub.amazonaws.com'
        )
    
    def test_enable_delegated_administrator_already_exists(self, security_hub_manager, mock_aws_client):
        """Test delegated administrator already exists."""
        mock_orgs = Mock()
        mock_orgs.register_delegated_administrator.side_effect = ClientError(
            {'Error': {'Code': 'AccountAlreadyRegisteredException'}}, 'RegisterDelegatedAdministrator'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = security_hub_manager.enable_delegated_administrator('123456789012')
        
        assert result is True
    
    def test_enable_delegated_administrator_failure(self, security_hub_manager, mock_aws_client):
        """Test delegated administrator enablement failure."""
        mock_orgs = Mock()
        mock_orgs.register_delegated_administrator.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'RegisterDelegatedAdministrator'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        with pytest.raises(SecurityHubOrganizationError):
            security_hub_manager.enable_delegated_administrator('123456789012')
    
    def test_enable_organization_security_hub_success(self, security_hub_manager, mock_aws_client):
        """Test Security Hub organization setup success."""
        mock_securityhub = Mock()
        mock_aws_client.get_client.return_value = mock_securityhub
        
        result = security_hub_manager.enable_organization_security_hub()
        
        assert result['auto_enable'] is True
        assert result['auto_enable_standards'] == 'DEFAULT'
        mock_securityhub.enable_security_hub.assert_called_once()
        mock_securityhub.update_organization_configuration.assert_called_once_with(
            AutoEnable=True,
            AutoEnableStandards='DEFAULT'
        )
    
    def test_enable_organization_security_hub_already_enabled(self, security_hub_manager, mock_aws_client):
        """Test Security Hub organization setup when already enabled."""
        mock_securityhub = Mock()
        mock_securityhub.enable_security_hub.side_effect = ClientError(
            {'Error': {'Code': 'ResourceConflictException'}}, 'EnableSecurityHub'
        )
        mock_aws_client.get_client.return_value = mock_securityhub
        
        result = security_hub_manager.enable_organization_security_hub(auto_enable=False)
        
        assert result['auto_enable'] is False
        mock_securityhub.update_organization_configuration.assert_called_once()
    
    def test_enable_organization_security_hub_failure(self, security_hub_manager, mock_aws_client):
        """Test Security Hub organization setup failure."""
        mock_securityhub = Mock()
        mock_securityhub.enable_security_hub.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'EnableSecurityHub'
        )
        mock_aws_client.get_client.return_value = mock_securityhub
        
        with pytest.raises(SecurityHubOrganizationError):
            security_hub_manager.enable_organization_security_hub()
    
    def test_enable_foundational_standards_success(self, security_hub_manager, mock_aws_client):
        """Test successful foundational standards enablement."""
        mock_securityhub = Mock()
        mock_securityhub.describe_standards.return_value = {
            'Standards': [
                {
                    'StandardsArn': 'arn:aws:securityhub:::standard/aws-foundational-security-best-practices',
                    'Name': 'AWS Foundational Security Best Practices'
                },
                {
                    'StandardsArn': 'arn:aws:securityhub:::standard/cis-aws-foundations-benchmark',
                    'Name': 'CIS AWS Foundations Benchmark'
                }
            ]
        }
        mock_securityhub.batch_enable_standards.return_value = {
            'StandardsSubscriptions': [{'StandardsArn': 'test-arn'}]
        }
        mock_aws_client.get_client.return_value = mock_securityhub
        
        result = security_hub_manager.enable_foundational_standards()
        
        assert len(result) == 2
        assert mock_securityhub.batch_enable_standards.call_count == 2
    
    def test_enable_foundational_standards_already_enabled(self, security_hub_manager, mock_aws_client):
        """Test foundational standards enablement when already enabled."""
        mock_securityhub = Mock()
        mock_securityhub.describe_standards.return_value = {
            'Standards': [
                {
                    'StandardsArn': 'arn:aws:securityhub:::standard/aws-foundational-security-best-practices',
                    'Name': 'AWS Foundational Security Best Practices'
                }
            ]
        }
        mock_securityhub.batch_enable_standards.side_effect = ClientError(
            {'Error': {'Code': 'ResourceConflictException'}}, 'BatchEnableStandards'
        )
        mock_aws_client.get_client.return_value = mock_securityhub
        
        result = security_hub_manager.enable_foundational_standards()
        
        assert len(result) == 0
    
    def test_validate_security_hub_setup_success(self, security_hub_manager, mock_aws_client):
        """Test successful Security Hub setup validation."""
        mock_orgs = Mock()
        mock_orgs.list_aws_service_access_for_organization.return_value = {
            'EnabledServicePrincipals': [{'ServicePrincipal': 'securityhub.amazonaws.com'}]
        }
        mock_orgs.list_delegated_administrators.return_value = {
            'DelegatedAdministrators': [{'Id': '123456789012'}]
        }
        
        mock_securityhub = Mock()
        mock_securityhub.get_enabled_standards.return_value = {
            'StandardsSubscriptions': [{'StandardsArn': 'test-arn'}]
        }
        mock_securityhub.describe_organization_configuration.return_value = {'AutoEnable': True}
        
        mock_aws_client.get_client.side_effect = lambda service: mock_orgs if service == 'organizations' else mock_securityhub
        
        result = security_hub_manager.validate_security_hub_setup()
        
        assert result['service_access'] is True
        assert result['delegated_admin'] is True
        assert result['security_hub_enabled'] is True
        assert result['organization_config'] is True
        assert result['standards_enabled'] is True
    
    def test_validate_security_hub_setup_failure(self, security_hub_manager, mock_aws_client):
        """Test Security Hub setup validation with failures."""
        mock_orgs = Mock()
        mock_orgs.list_aws_service_access_for_organization.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'ListAWSServiceAccessForOrganization'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = security_hub_manager.validate_security_hub_setup()
        
        assert result['service_access'] is False
        assert result['delegated_admin'] is False
        assert result['security_hub_enabled'] is False
        assert result['organization_config'] is False
        assert result['standards_enabled'] is False
