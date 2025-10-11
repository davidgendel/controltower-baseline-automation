"""Tests for Control Tower deployment functionality."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.control_tower.deployer import (
    ControlTowerDeployer, 
    ControlTowerError, 
    DeploymentError
)
from src.core.aws_client import AWSClientManager


class TestControlTowerDeployer:
    """Test cases for ControlTowerDeployer class."""
    
    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create mock AWS client manager."""
        manager = Mock(spec=AWSClientManager)
        mock_client = Mock()
        manager.get_client.return_value = mock_client
        return manager
    
    @pytest.fixture
    def deployer(self, mock_aws_client_manager):
        """Create ControlTowerDeployer instance."""
        return ControlTowerDeployer(mock_aws_client_manager)
    
    @pytest.fixture
    def valid_manifest(self):
        """Create valid landing zone manifest."""
        return {
            'governedRegions': ['us-east-1', 'us-west-2'],
            'organizationStructure': {
                'security': {'name': 'Security'},
                'sandbox': {'name': 'Sandbox'}
            },
            'centralizedLogging': {
                'accountId': '111111111111',
                'enabled': True
            },
            'securityRoles': {
                'accountId': '222222222222'
            },
            'accessManagement': {
                'enabled': True
            }
        }
    
    def test_init(self, mock_aws_client_manager):
        """Test deployer initialization."""
        deployer = ControlTowerDeployer(mock_aws_client_manager)
        
        assert deployer.aws_client_manager == mock_aws_client_manager
        assert deployer._control_tower_client is None
    
    def test_control_tower_client_property(self, deployer, mock_aws_client_manager):
        """Test lazy initialization of Control Tower client."""
        # First access should create client
        client = deployer.control_tower_client
        mock_aws_client_manager.get_client.assert_called_once_with('controltower')
        
        # Second access should return same client
        client2 = deployer.control_tower_client
        assert client == client2
        assert mock_aws_client_manager.get_client.call_count == 1
    
    def test_create_landing_zone_success(self, deployer, valid_manifest):
        """Test successful landing zone creation."""
        # Mock successful API response
        mock_response = {
            'arn': 'arn:aws:controltower:us-east-1:123456789012:landingzone/test-lz',
            'operationIdentifier': 'op-12345678-1234-1234-1234-123456789012'
        }
        deployer.control_tower_client.create_landing_zone.return_value = mock_response
        
        # Test creation
        operation_id = deployer.create_landing_zone(valid_manifest)
        
        assert operation_id == 'op-12345678-1234-1234-1234-123456789012'
        
        # Verify API call
        deployer.control_tower_client.create_landing_zone.assert_called_once_with(
            manifest=valid_manifest,
            version='3.3'
        )
    
    def test_create_landing_zone_with_custom_version_and_tags(self, deployer, valid_manifest):
        """Test landing zone creation with custom version and tags."""
        mock_response = {
            'arn': 'arn:aws:controltower:us-east-1:123456789012:landingzone/test-lz',
            'operationIdentifier': 'op-12345678-1234-1234-1234-123456789012'
        }
        deployer.control_tower_client.create_landing_zone.return_value = mock_response
        
        tags = {'Environment': 'Production', 'Team': 'Platform'}
        operation_id = deployer.create_landing_zone(valid_manifest, version='3.2', tags=tags)
        
        assert operation_id == 'op-12345678-1234-1234-1234-123456789012'
        
        deployer.control_tower_client.create_landing_zone.assert_called_once_with(
            manifest=valid_manifest,
            version='3.2',
            tags=tags
        )
    
    def test_create_landing_zone_validation_error(self, deployer):
        """Test landing zone creation with validation error."""
        # Test local validation error first
        with pytest.raises(ControlTowerError, match="Missing required field in manifest"):
            deployer.create_landing_zone({})
    
    def test_create_landing_zone_api_validation_error(self, deployer, valid_manifest):
        """Test landing zone creation with API validation error."""
        error_response = {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Invalid manifest structure'
            }
        }
        deployer.control_tower_client.create_landing_zone.side_effect = ClientError(
            error_response, 'CreateLandingZone'
        )
        
        with pytest.raises(ControlTowerError, match="Invalid manifest or parameters"):
            deployer.create_landing_zone(valid_manifest)
    
    def test_create_landing_zone_conflict_error(self, deployer, valid_manifest):
        """Test landing zone creation with conflict error."""
        error_response = {
            'Error': {
                'Code': 'ConflictException',
                'Message': 'Landing zone already exists'
            }
        }
        deployer.control_tower_client.create_landing_zone.side_effect = ClientError(
            error_response, 'CreateLandingZone'
        )
        
        with pytest.raises(DeploymentError, match="Landing zone already exists"):
            deployer.create_landing_zone(valid_manifest)
    
    def test_create_landing_zone_access_denied(self, deployer, valid_manifest):
        """Test landing zone creation with access denied error."""
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Insufficient permissions'
            }
        }
        deployer.control_tower_client.create_landing_zone.side_effect = ClientError(
            error_response, 'CreateLandingZone'
        )
        
        with pytest.raises(DeploymentError, match="Insufficient permissions"):
            deployer.create_landing_zone(valid_manifest)
    
    def test_get_landing_zone_status_success(self, deployer):
        """Test successful status retrieval."""
        mock_response = {
            'operationDetails': {
                'status': 'IN_PROGRESS',
                'operationType': 'CREATE',
                'startTime': '2023-01-01T00:00:00Z',
                'endTime': None,
                'statusMessage': None
            }
        }
        deployer.control_tower_client.get_landing_zone_operation.return_value = mock_response
        
        status = deployer.get_landing_zone_status('op-12345')
        
        expected_status = {
            'status': 'IN_PROGRESS',
            'operation_type': 'CREATE',
            'start_time': '2023-01-01T00:00:00Z',
            'end_time': None,
            'status_message': None
        }
        assert status == expected_status
    
    def test_get_landing_zone_status_error(self, deployer):
        """Test status retrieval error."""
        error_response = {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Invalid operation ID'
            }
        }
        deployer.control_tower_client.get_landing_zone_operation.side_effect = ClientError(
            error_response, 'GetLandingZoneOperation'
        )
        
        with pytest.raises(ControlTowerError, match="Failed to get operation status"):
            deployer.get_landing_zone_status('invalid-op-id')
    
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_deployment_success(self, mock_time, mock_sleep, deployer):
        """Test successful deployment monitoring."""
        # Mock time progression
        mock_time.side_effect = [0, 30, 60, 90]  # Start, then 3 checks
        
        # Mock status progression
        status_responses = [
            {'status': 'IN_PROGRESS', 'operation_type': 'CREATE', 'start_time': '2023-01-01T00:00:00Z', 'end_time': None, 'status_message': None},
            {'status': 'IN_PROGRESS', 'operation_type': 'CREATE', 'start_time': '2023-01-01T00:00:00Z', 'end_time': None, 'status_message': None},
            {'status': 'SUCCEEDED', 'operation_type': 'CREATE', 'start_time': '2023-01-01T00:00:00Z', 'end_time': '2023-01-01T00:01:30Z', 'status_message': None}
        ]
        
        deployer.get_landing_zone_status = Mock(side_effect=status_responses)
        
        result = deployer.wait_for_deployment_completion('op-12345', timeout_seconds=300)
        
        assert result is True
        assert deployer.get_landing_zone_status.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep called between checks
    
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_deployment_failure(self, mock_time, mock_sleep, deployer):
        """Test deployment monitoring with failure."""
        # Mock time progression - need more values for the loop
        mock_time.side_effect = [0, 30, 60]  # Start, first check, second check
        
        status_responses = [
            {'status': 'IN_PROGRESS', 'operation_type': 'CREATE', 'start_time': '2023-01-01T00:00:00Z', 'end_time': None, 'status_message': None},
            {'status': 'FAILED', 'operation_type': 'CREATE', 'start_time': '2023-01-01T00:00:00Z', 'end_time': '2023-01-01T00:00:30Z', 'status_message': 'Deployment failed due to insufficient permissions'}
        ]
        
        deployer.get_landing_zone_status = Mock(side_effect=status_responses)
        
        with pytest.raises(DeploymentError, match="Deployment failed: Deployment failed due to insufficient permissions"):
            deployer.wait_for_deployment_completion('op-12345', timeout_seconds=300)
    
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_deployment_timeout(self, mock_time, mock_sleep, deployer):
        """Test deployment monitoring timeout."""
        # Mock time to exceed timeout - need more values
        mock_time.side_effect = [0, 150, 301]  # Start, mid-way, then exceed 300s timeout
        
        status_response = {'status': 'IN_PROGRESS', 'operation_type': 'CREATE', 'start_time': '2023-01-01T00:00:00Z', 'end_time': None, 'status_message': None}
        deployer.get_landing_zone_status = Mock(return_value=status_response)
        
        with pytest.raises(DeploymentError, match="Deployment timeout after 5 minutes"):
            deployer.wait_for_deployment_completion('op-12345', timeout_seconds=300)
    
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_deployment_keyboard_interrupt(self, mock_time, mock_sleep, deployer):
        """Test deployment monitoring with keyboard interrupt."""
        mock_time.side_effect = [0, 30, 60]  # Need more values
        mock_sleep.side_effect = KeyboardInterrupt()
        
        status_response = {'status': 'IN_PROGRESS', 'operation_type': 'CREATE', 'start_time': '2023-01-01T00:00:00Z', 'end_time': None, 'status_message': None}
        deployer.get_landing_zone_status = Mock(return_value=status_response)
        
        with pytest.raises(DeploymentError, match="Deployment monitoring interrupted"):
            deployer.wait_for_deployment_completion('op-12345', timeout_seconds=300)
    
    def test_get_landing_zone_details_success(self, deployer):
        """Test successful landing zone details retrieval."""
        mock_response = {
            'landingZone': {
                'arn': 'arn:aws:controltower:us-east-1:123456789012:landingzone/test-lz',
                'status': 'ACTIVE',
                'latestAvailableVersion': '3.3',
                'version': '3.3',
                'manifest': {'governedRegions': ['us-east-1']},
                'driftStatus': {'status': 'DRIFTED'}
            }
        }
        deployer.control_tower_client.get_landing_zone.return_value = mock_response
        
        details = deployer.get_landing_zone_details('arn:aws:controltower:us-east-1:123456789012:landingzone/test-lz')
        
        expected_details = {
            'arn': 'arn:aws:controltower:us-east-1:123456789012:landingzone/test-lz',
            'status': 'ACTIVE',
            'latest_available_version': '3.3',
            'version': '3.3',
            'manifest': {'governedRegions': ['us-east-1']},
            'drift_status': {'status': 'DRIFTED'}
        }
        assert details == expected_details
    
    def test_get_landing_zone_details_error(self, deployer):
        """Test landing zone details retrieval error."""
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Landing zone not found'
            }
        }
        deployer.control_tower_client.get_landing_zone.side_effect = ClientError(
            error_response, 'GetLandingZone'
        )
        
        with pytest.raises(ControlTowerError, match="Failed to get landing zone details"):
            deployer.get_landing_zone_details('invalid-arn')
    
    def test_validate_manifest_success(self, deployer, valid_manifest):
        """Test successful manifest validation."""
        # Should not raise any exception
        deployer._validate_manifest(valid_manifest)
    
    def test_validate_manifest_missing_required_field(self, deployer):
        """Test manifest validation with missing required field."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}}
            # Missing centralizedLogging and securityRoles
        }
        
        with pytest.raises(ControlTowerError, match="Missing required field in manifest: centralizedLogging"):
            deployer._validate_manifest(invalid_manifest)
    
    def test_validate_manifest_empty_governed_regions(self, deployer):
        """Test manifest validation with empty governed regions."""
        invalid_manifest = {
            'governedRegions': [],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ControlTowerError, match="governedRegions must be a non-empty list"):
            deployer._validate_manifest(invalid_manifest)
    
    def test_validate_manifest_missing_security_ou(self, deployer):
        """Test manifest validation with missing security OU."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'sandbox': {'name': 'Sandbox'}},  # Missing security
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ControlTowerError, match="organizationStructure must contain 'security' OU"):
            deployer._validate_manifest(invalid_manifest)
    
    def test_validate_manifest_missing_logging_account_id(self, deployer):
        """Test manifest validation with missing logging account ID."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'enabled': True},  # Missing accountId
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ControlTowerError, match="centralizedLogging must contain 'accountId'"):
            deployer._validate_manifest(invalid_manifest)
    
    def test_validate_manifest_missing_security_account_id(self, deployer):
        """Test manifest validation with missing security account ID."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {}  # Missing accountId
        }
        
        with pytest.raises(ControlTowerError, match="securityRoles must contain 'accountId'"):
            deployer._validate_manifest(invalid_manifest)
    
    def test_validate_manifest_same_account_ids(self, deployer):
        """Test manifest validation with same account IDs for logging and security."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '111111111111'}  # Same as logging
        }
        
        with pytest.raises(ControlTowerError, match="centralizedLogging and securityRoles must use different account IDs"):
            deployer._validate_manifest(invalid_manifest)
