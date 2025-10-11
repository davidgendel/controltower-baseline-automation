"""Tests for IAM roles management functionality."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.prerequisites.iam_roles import IAMRolesManager, IAMRoleError
from src.core.aws_client import AWSClientManager


@pytest.fixture
def mock_aws_client():
    """Mock AWS client manager."""
    client = Mock(spec=AWSClientManager)
    client.get_current_region.return_value = 'us-east-1'
    return client


@pytest.fixture
def mock_iam_client():
    """Mock IAM client."""
    return Mock()


@pytest.fixture
def iam_manager(mock_aws_client, mock_iam_client):
    """IAM roles manager with mocked client."""
    manager = IAMRolesManager(mock_aws_client)
    mock_aws_client.get_client.return_value = mock_iam_client
    return manager


class TestIAMRolesManager:
    """Test IAMRolesManager class."""

    def test_init(self, mock_aws_client):
        """Test IAMRolesManager initialization."""
        manager = IAMRolesManager(mock_aws_client)
        assert manager.aws_client == mock_aws_client
        assert manager._iam_client is None

    def test_get_client(self, iam_manager, mock_aws_client, mock_iam_client):
        """Test client initialization and caching."""
        client = iam_manager._get_client()
        assert client == mock_iam_client
        mock_aws_client.get_client.assert_called_once_with('iam', 'us-east-1')
        
        # Second call should use cached client
        client2 = iam_manager._get_client()
        assert client2 == mock_iam_client
        assert mock_aws_client.get_client.call_count == 1

    def test_role_exists_true(self, iam_manager, mock_iam_client):
        """Test role existence check when role exists."""
        mock_iam_client.get_role.return_value = {'Role': {'RoleName': 'TestRole'}}
        
        result = iam_manager.role_exists('TestRole')
        assert result is True
        mock_iam_client.get_role.assert_called_once_with(RoleName='TestRole')

    def test_role_exists_false(self, iam_manager, mock_iam_client):
        """Test role existence check when role doesn't exist."""
        mock_iam_client.get_role.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchEntity'}}, 'GetRole'
        )
        
        result = iam_manager.role_exists('TestRole')
        assert result is False

    def test_role_exists_error(self, iam_manager, mock_iam_client):
        """Test role existence check with other errors."""
        mock_iam_client.get_role.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'GetRole'
        )
        
        with pytest.raises(IAMRoleError, match="Failed to check role"):
            iam_manager.role_exists('TestRole')

    def test_get_role_details_success(self, iam_manager, mock_iam_client):
        """Test getting role details successfully."""
        expected_role = {'RoleName': 'TestRole', 'Arn': 'arn:aws:iam::123456789012:role/TestRole'}
        mock_iam_client.get_role.return_value = {'Role': expected_role}
        
        result = iam_manager.get_role_details('TestRole')
        assert result == expected_role

    def test_get_role_details_not_found(self, iam_manager, mock_iam_client):
        """Test getting role details when role not found."""
        mock_iam_client.get_role.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchEntity'}}, 'GetRole'
        )
        
        result = iam_manager.get_role_details('TestRole')
        assert result is None

    def test_get_role_details_error(self, iam_manager, mock_iam_client):
        """Test getting role details with error."""
        mock_iam_client.get_role.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'GetRole'
        )
        
        with pytest.raises(IAMRoleError, match="Failed to get role details"):
            iam_manager.get_role_details('TestRole')

    def test_validate_role_trust_policy_valid(self, iam_manager):
        """Test trust policy validation with valid policy."""
        role_details = {
            'AssumeRolePolicyDocument': {
                'Statement': [{
                    'Principal': {'Service': 'controltower.amazonaws.com'},
                    'Effect': 'Allow',
                    'Action': 'sts:AssumeRole'
                }]
            }
        }
        
        with patch.object(iam_manager, 'get_role_details', return_value=role_details):
            result = iam_manager.validate_role_trust_policy('AWSControlTowerAdmin')
            assert result is True

    def test_validate_role_trust_policy_invalid(self, iam_manager):
        """Test trust policy validation with invalid policy."""
        role_details = {
            'AssumeRolePolicyDocument': {
                'Statement': [{
                    'Principal': {'Service': 'ec2.amazonaws.com'},
                    'Effect': 'Allow',
                    'Action': 'sts:AssumeRole'
                }]
            }
        }
        
        with patch.object(iam_manager, 'get_role_details', return_value=role_details):
            result = iam_manager.validate_role_trust_policy('AWSControlTowerAdmin')
            assert result is False

    def test_validate_role_trust_policy_no_role(self, iam_manager):
        """Test trust policy validation when role doesn't exist."""
        with patch.object(iam_manager, 'get_role_details', return_value=None):
            result = iam_manager.validate_role_trust_policy('AWSControlTowerAdmin')
            assert result is False

    def test_validate_role_trust_policy_unknown_role(self, iam_manager):
        """Test trust policy validation for unknown role."""
        role_details = {'AssumeRolePolicyDocument': {}}
        
        with patch.object(iam_manager, 'get_role_details', return_value=role_details):
            result = iam_manager.validate_role_trust_policy('UnknownRole')
            assert result is True  # Skip validation for unknown roles

    def test_validate_control_tower_roles(self, iam_manager):
        """Test validation of all Control Tower roles."""
        with patch.object(iam_manager, 'role_exists') as mock_exists:
            mock_exists.side_effect = [True, False, True]  # Mixed results
            
            result = iam_manager.validate_control_tower_roles()
            
            assert len(result) == 3
            assert result['AWSControlTowerAdmin'] is True
            assert result['AWSControlTowerStackSetRole'] is False
            assert result['AWSControlTowerCloudTrailRole'] is True

    def test_get_missing_roles(self, iam_manager):
        """Test getting list of missing roles."""
        with patch.object(iam_manager, 'validate_control_tower_roles') as mock_validate:
            mock_validate.return_value = {
                'AWSControlTowerAdmin': True,
                'AWSControlTowerStackSetRole': False,
                'AWSControlTowerCloudTrailRole': False
            }
            
            missing = iam_manager.get_missing_roles()
            assert len(missing) == 2
            assert 'AWSControlTowerStackSetRole' in missing
            assert 'AWSControlTowerCloudTrailRole' in missing

    def test_get_roles_summary(self, iam_manager):
        """Test getting roles summary."""
        with patch.object(iam_manager, 'role_exists') as mock_exists, \
             patch.object(iam_manager, 'validate_role_trust_policy') as mock_trust:
            
            mock_exists.side_effect = [True, False, True]
            mock_trust.side_effect = [True, False, False]  # Trust policy results
            
            summary = iam_manager.get_roles_summary()
            
            assert summary['total_roles'] == 3
            assert summary['existing_roles'] == 2
            assert len(summary['missing_roles']) == 1
            assert 'AWSControlTowerStackSetRole' in summary['missing_roles']
            
            # Check role details
            assert summary['role_details']['AWSControlTowerAdmin']['exists'] is True
            assert summary['role_details']['AWSControlTowerAdmin']['trust_policy_valid'] is True
            assert summary['role_details']['AWSControlTowerStackSetRole']['exists'] is False
            assert summary['role_details']['AWSControlTowerCloudTrailRole']['exists'] is True
            assert summary['role_details']['AWSControlTowerCloudTrailRole']['trust_policy_valid'] is False
