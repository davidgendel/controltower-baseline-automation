"""Unit tests for GuardDuty organization management."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.post_deployment.guardduty import GuardDutyOrganizationManager, GuardDutyOrganizationError
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
def guardduty_manager(mock_config, mock_aws_client):
    return GuardDutyOrganizationManager(mock_config, mock_aws_client)


class TestGuardDutyOrganizationManager:
    
    def test_enable_delegated_administrator_success(self, guardduty_manager, mock_aws_client):
        """Test successful delegated administrator enablement."""
        mock_orgs = Mock()
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = guardduty_manager.enable_delegated_administrator('123456789012')
        
        assert result is True
        mock_orgs.enable_aws_service_access.assert_called_once_with(
            ServicePrincipal='guardduty.amazonaws.com'
        )
        mock_orgs.register_delegated_administrator.assert_called_once_with(
            AccountId='123456789012',
            ServicePrincipal='guardduty.amazonaws.com'
        )
    
    def test_enable_delegated_administrator_already_exists(self, guardduty_manager, mock_aws_client):
        """Test delegated administrator already exists."""
        mock_orgs = Mock()
        mock_orgs.register_delegated_administrator.side_effect = ClientError(
            {'Error': {'Code': 'AccountAlreadyRegisteredException'}}, 'RegisterDelegatedAdministrator'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = guardduty_manager.enable_delegated_administrator('123456789012')
        
        assert result is True
    
    def test_enable_delegated_administrator_failure(self, guardduty_manager, mock_aws_client):
        """Test delegated administrator enablement failure."""
        mock_orgs = Mock()
        mock_orgs.register_delegated_administrator.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'RegisterDelegatedAdministrator'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        with pytest.raises(GuardDutyOrganizationError):
            guardduty_manager.enable_delegated_administrator('123456789012')
    
    def test_enable_organization_guardduty_new_detector(self, guardduty_manager, mock_aws_client):
        """Test GuardDuty organization setup with new detector."""
        mock_guardduty = Mock()
        mock_guardduty.list_detectors.return_value = {'DetectorIds': []}
        mock_guardduty.create_detector.return_value = {'DetectorId': 'detector-123'}
        mock_aws_client.get_client.return_value = mock_guardduty
        
        result = guardduty_manager.enable_organization_guardduty()
        
        assert result['detector_id'] == 'detector-123'
        assert result['auto_enable'] is True
        mock_guardduty.create_detector.assert_called_once_with(Enable=True)
        mock_guardduty.update_organization_configuration.assert_called_once()
    
    def test_enable_organization_guardduty_existing_detector(self, guardduty_manager, mock_aws_client):
        """Test GuardDuty organization setup with existing detector."""
        mock_guardduty = Mock()
        mock_guardduty.list_detectors.return_value = {'DetectorIds': ['detector-456']}
        mock_aws_client.get_client.return_value = mock_guardduty
        
        result = guardduty_manager.enable_organization_guardduty(auto_enable=False)
        
        assert result['detector_id'] == 'detector-456'
        assert result['auto_enable'] is False
        mock_guardduty.create_detector.assert_not_called()
        mock_guardduty.update_organization_configuration.assert_called_once()
    
    def test_enable_organization_guardduty_failure(self, guardduty_manager, mock_aws_client):
        """Test GuardDuty organization setup failure."""
        mock_guardduty = Mock()
        mock_guardduty.list_detectors.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'ListDetectors'
        )
        mock_aws_client.get_client.return_value = mock_guardduty
        
        with pytest.raises(GuardDutyOrganizationError):
            guardduty_manager.enable_organization_guardduty()
    
    def test_set_finding_frequency_success(self, guardduty_manager, mock_aws_client):
        """Test successful finding frequency setting."""
        mock_guardduty = Mock()
        mock_guardduty.list_detectors.return_value = {'DetectorIds': ['detector-123']}
        mock_aws_client.get_client.return_value = mock_guardduty
        
        result = guardduty_manager.set_finding_frequency('ONE_HOUR')
        
        assert result is True
        mock_guardduty.update_detector.assert_called_once_with(
            DetectorId='detector-123',
            FindingPublishingFrequency='ONE_HOUR'
        )
    
    def test_set_finding_frequency_no_detector(self, guardduty_manager, mock_aws_client):
        """Test finding frequency setting with no detector."""
        mock_guardduty = Mock()
        mock_guardduty.list_detectors.return_value = {'DetectorIds': []}
        mock_aws_client.get_client.return_value = mock_guardduty
        
        with pytest.raises(GuardDutyOrganizationError, match="No GuardDuty detector found"):
            guardduty_manager.set_finding_frequency()
    
    def test_validate_guardduty_setup_success(self, guardduty_manager, mock_aws_client):
        """Test successful GuardDuty setup validation."""
        mock_orgs = Mock()
        mock_orgs.list_aws_service_access_for_organization.return_value = {
            'EnabledServicePrincipals': [{'ServicePrincipal': 'guardduty.amazonaws.com'}]
        }
        mock_orgs.list_delegated_administrators.return_value = {
            'DelegatedAdministrators': [{'Id': '123456789012'}]
        }
        
        mock_guardduty = Mock()
        mock_guardduty.list_detectors.return_value = {'DetectorIds': ['detector-123']}
        mock_guardduty.describe_organization_configuration.return_value = {'AutoEnable': True}
        
        mock_aws_client.get_client.side_effect = lambda service: mock_orgs if service == 'organizations' else mock_guardduty
        
        result = guardduty_manager.validate_guardduty_setup()
        
        assert result['service_access'] is True
        assert result['delegated_admin'] is True
        assert result['detector_enabled'] is True
        assert result['organization_config'] is True
    
    def test_validate_guardduty_setup_failure(self, guardduty_manager, mock_aws_client):
        """Test GuardDuty setup validation with failures."""
        mock_orgs = Mock()
        mock_orgs.list_aws_service_access_for_organization.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'ListAWSServiceAccessForOrganization'
        )
        mock_aws_client.get_client.return_value = mock_orgs
        
        result = guardduty_manager.validate_guardduty_setup()
        
        assert result['service_access'] is False
        assert result['delegated_admin'] is False
        assert result['detector_enabled'] is False
        assert result['organization_config'] is False
