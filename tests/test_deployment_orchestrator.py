"""Tests for Control Tower deployment orchestration functionality."""

import pytest
from unittest.mock import Mock, patch
from src.control_tower.orchestrator import (
    DeploymentOrchestrator, 
    DeploymentOrchestrationError
)
from src.control_tower.deployer import DeploymentError
from src.control_tower.manifest import ManifestValidationError
from src.control_tower.scp_policies import SCPPolicyError
from src.core.aws_client import AWSClientManager
from src.core.config import Configuration


class TestDeploymentOrchestrator:
    """Test cases for DeploymentOrchestrator class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.aws = Mock()
        config.aws.home_region = 'us-east-1'
        config.organization = Mock()
        config.organization.security_ou_name = 'Security'
        config.organization.additional_ous = []
        config.scp_tier = 'standard'
        config.landing_zone_version = '3.3'
        config.get_scp_tier.return_value = 'standard'  # Fix mock method return
        return config
    
    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create mock AWS client manager."""
        return Mock(spec=AWSClientManager)
    
    @pytest.fixture
    def orchestrator(self, mock_config, mock_aws_client_manager):
        """Create DeploymentOrchestrator instance."""
        return DeploymentOrchestrator(mock_config, mock_aws_client_manager)
    
    @pytest.fixture
    def mock_manifest(self):
        """Create mock manifest."""
        return {
            'governedRegions': ['us-east-1', 'us-west-2'],
            'organizationStructure': {
                'security': {'name': 'Security'}
            },
            'centralizedLogging': {
                'accountId': '111111111111',
                'enabled': True
            },
            'securityRoles': {
                'accountId': '222222222222'
            }
        }
    
    def test_init(self, mock_config, mock_aws_client_manager):
        """Test orchestrator initialization."""
        orchestrator = DeploymentOrchestrator(mock_config, mock_aws_client_manager)
        
        assert orchestrator.config == mock_config
        assert orchestrator.aws_client_manager == mock_aws_client_manager
        assert orchestrator.prerequisites_validator is not None
        assert orchestrator.manifest_generator is not None
        assert orchestrator.control_tower_deployer is not None
        assert orchestrator.scp_policy_manager is not None
        
        # Check initial deployment state
        expected_state = {
            'prerequisites_validated': False,
            'manifest_generated': False,
            'control_tower_deployed': False,
            'scp_policies_deployed': False,
            'deployment_validated': False,
            'audit_account_id': None,
            'landing_zone_arn': None
        }
        assert orchestrator.deployment_state == expected_state
    
    def test_orchestrate_deployment_success_full(self, orchestrator, mock_manifest):
        """Test successful full deployment orchestration."""
        # Mock all component methods
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={'test': {'is_valid': True, 'message': 'All good'}}
        )
        orchestrator.manifest_generator.generate_manifest = Mock(return_value=mock_manifest)
        orchestrator.control_tower_deployer.create_landing_zone = Mock(return_value='op-12345')
        orchestrator.control_tower_deployer.wait_for_deployment_completion = Mock(return_value=True)
        orchestrator.control_tower_deployer.get_landing_zone_details = Mock(
            return_value={'status': 'ACTIVE', 'drift_status': {'status': 'IN_SYNC'}}
        )
        orchestrator.scp_policy_manager.deploy_scp_tier = Mock(
            return_value={'Policy1': 'policy-id-1', 'Policy2': 'policy-id-2'}
        )
        orchestrator._get_target_ous_for_scp = Mock(return_value=['ou-12345'])
        
        result = orchestrator.orchestrate_deployment()
        
        # Verify results
        assert result['status'] == 'SUCCESS'
        assert 'prerequisites_validation' in result['steps_completed']
        assert 'manifest_generation' in result['steps_completed']
        assert 'control_tower_deployment' in result['steps_completed']
        assert 'scp_policy_deployment' in result['steps_completed']
        assert 'post_deployment_validation' in result['steps_completed']
        assert result['operation_id'] == 'op-12345'
        assert result['landing_zone_arn'] is not None
        assert len(result['deployed_policies']) == 2
        assert len(result['errors']) == 0
        
        # Verify deployment state
        assert orchestrator.deployment_state['prerequisites_validated'] is True
        assert orchestrator.deployment_state['manifest_generated'] is True
        assert orchestrator.deployment_state['control_tower_deployed'] is True
        assert orchestrator.deployment_state['scp_policies_deployed'] is True
        assert orchestrator.deployment_state['deployment_validated'] is True
    
    def test_orchestrate_deployment_success_skip_prerequisites(self, orchestrator, mock_manifest):
        """Test successful deployment with skipped prerequisites."""
        # Mock component methods (skip prerequisites validation)
        orchestrator.manifest_generator.generate_manifest = Mock(return_value=mock_manifest)
        orchestrator.control_tower_deployer.create_landing_zone = Mock(return_value='op-12345')
        orchestrator.control_tower_deployer.wait_for_deployment_completion = Mock(return_value=True)
        orchestrator.control_tower_deployer.get_landing_zone_details = Mock(
            return_value={'status': 'ACTIVE', 'drift_status': {'status': 'IN_SYNC'}}
        )
        orchestrator.scp_policy_manager.deploy_scp_tier = Mock(return_value={})
        orchestrator._get_target_ous_for_scp = Mock(return_value=['ou-12345'])
        
        result = orchestrator.orchestrate_deployment(skip_prerequisites=True)
        
        assert result['status'] == 'SUCCESS'
        assert 'prerequisites_validation' not in result['steps_completed']
        assert 'manifest_generation' in result['steps_completed']
        assert orchestrator.deployment_state['prerequisites_validated'] is False
    
    def test_orchestrate_deployment_success_skip_scp(self, orchestrator, mock_manifest):
        """Test successful deployment with skipped SCP deployment."""
        # Mock component methods
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={'test': {'is_valid': True, 'message': 'All good'}}
        )
        orchestrator.manifest_generator.generate_manifest = Mock(return_value=mock_manifest)
        orchestrator.control_tower_deployer.create_landing_zone = Mock(return_value='op-12345')
        orchestrator.control_tower_deployer.wait_for_deployment_completion = Mock(return_value=True)
        orchestrator.control_tower_deployer.get_landing_zone_details = Mock(
            return_value={'status': 'ACTIVE', 'drift_status': {'status': 'IN_SYNC'}}
        )
        
        result = orchestrator.orchestrate_deployment(skip_scp_deployment=True)
        
        assert result['status'] == 'SUCCESS'
        assert 'scp_policy_deployment' not in result['steps_completed']
        assert orchestrator.deployment_state['scp_policies_deployed'] is False
    
    def test_orchestrate_deployment_prerequisites_failure(self, orchestrator):
        """Test deployment failure during prerequisites validation."""
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={
                'organizations': {'is_valid': False, 'message': 'Organizations not enabled'},
                'accounts': {'is_valid': True, 'message': 'Accounts OK'}
            }
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="Prerequisites validation failed"):
            orchestrator.orchestrate_deployment()
        
        # Verify deployment state
        assert orchestrator.deployment_state['prerequisites_validated'] is False
        assert orchestrator.deployment_state['manifest_generated'] is False
    
    def test_orchestrate_deployment_manifest_failure(self, orchestrator):
        """Test deployment failure during manifest generation."""
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={'test': {'is_valid': True, 'message': 'All good'}}
        )
        orchestrator.manifest_generator.generate_manifest = Mock(
            side_effect=ManifestValidationError("Invalid manifest")
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="Manifest generation failed"):
            orchestrator.orchestrate_deployment()
        
        assert orchestrator.deployment_state['prerequisites_validated'] is True
        assert orchestrator.deployment_state['manifest_generated'] is False
    
    def test_orchestrate_deployment_control_tower_failure(self, orchestrator, mock_manifest):
        """Test deployment failure during Control Tower deployment."""
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={'test': {'is_valid': True, 'message': 'All good'}}
        )
        orchestrator.manifest_generator.generate_manifest = Mock(return_value=mock_manifest)
        orchestrator.control_tower_deployer.create_landing_zone = Mock(
            side_effect=DeploymentError("Control Tower deployment failed")
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="Control Tower deployment failed"):
            orchestrator.orchestrate_deployment()
        
        assert orchestrator.deployment_state['manifest_generated'] is True
        assert orchestrator.deployment_state['control_tower_deployed'] is False
    
    def test_orchestrate_deployment_scp_failure(self, orchestrator, mock_manifest):
        """Test deployment failure during SCP policy deployment."""
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={'test': {'is_valid': True, 'message': 'All good'}}
        )
        orchestrator.manifest_generator.generate_manifest = Mock(return_value=mock_manifest)
        orchestrator.control_tower_deployer.create_landing_zone = Mock(return_value='op-12345')
        orchestrator.control_tower_deployer.wait_for_deployment_completion = Mock(return_value=True)
        orchestrator.scp_policy_manager.deploy_scp_tier = Mock(
            side_effect=SCPPolicyError("SCP deployment failed")
        )
        orchestrator._get_target_ous_for_scp = Mock(return_value=['ou-12345'])
        
        with pytest.raises(DeploymentOrchestrationError, match="SCP policy deployment failed"):
            orchestrator.orchestrate_deployment()
        
        assert orchestrator.deployment_state['control_tower_deployed'] is True
        assert orchestrator.deployment_state['scp_policies_deployed'] is False
    
    def test_orchestrate_deployment_validation_failure(self, orchestrator, mock_manifest):
        """Test deployment failure during post-deployment validation."""
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={'test': {'is_valid': True, 'message': 'All good'}}
        )
        orchestrator.manifest_generator.generate_manifest = Mock(return_value=mock_manifest)
        orchestrator.control_tower_deployer.create_landing_zone = Mock(return_value='op-12345')
        orchestrator.control_tower_deployer.wait_for_deployment_completion = Mock(return_value=True)
        orchestrator.control_tower_deployer.get_landing_zone_details = Mock(
            return_value={'status': 'FAILED', 'drift_status': {'status': 'IN_SYNC'}}
        )
        orchestrator.scp_policy_manager.deploy_scp_tier = Mock(return_value={})
        orchestrator._get_target_ous_for_scp = Mock(return_value=['ou-12345'])
        
        with pytest.raises(DeploymentOrchestrationError, match="Landing zone is not active"):
            orchestrator.orchestrate_deployment()
        
        assert orchestrator.deployment_state['scp_policies_deployed'] is True
        assert orchestrator.deployment_state['deployment_validated'] is False
    
    def test_get_deployment_status_success(self, orchestrator):
        """Test successful deployment status retrieval."""
        orchestrator.control_tower_deployer.get_landing_zone_status = Mock(
            return_value={
                'status': 'IN_PROGRESS',
                'operation_type': 'CREATE',
                'start_time': '2023-01-01T00:00:00Z',
                'end_time': None,
                'status_message': None
            }
        )
        
        status = orchestrator.get_deployment_status('op-12345')
        
        assert status['operation_id'] == 'op-12345'
        assert status['status'] == 'IN_PROGRESS'
        assert status['operation_type'] == 'CREATE'
        assert 'deployment_state' in status
    
    def test_get_deployment_status_failure(self, orchestrator):
        """Test deployment status retrieval failure."""
        orchestrator.control_tower_deployer.get_landing_zone_status = Mock(
            side_effect=Exception("Status retrieval failed")
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="Failed to get deployment status"):
            orchestrator.get_deployment_status('op-12345')
    
    def test_validate_prerequisites_success(self, orchestrator):
        """Test successful prerequisites validation."""
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={
                'organizations': {'is_valid': True, 'message': 'Organizations enabled'},
                'accounts': {'is_valid': True, 'message': 'Accounts configured'}
            }
        )
        
        # Should not raise exception
        orchestrator._validate_prerequisites()
        assert orchestrator.deployment_state['prerequisites_validated'] is True
    
    def test_validate_prerequisites_failure(self, orchestrator):
        """Test prerequisites validation failure."""
        orchestrator.prerequisites_validator.validate_all_prerequisites = Mock(
            return_value={
                'organizations': {'is_valid': False, 'message': 'Organizations not enabled'},
                'accounts': {'is_valid': True, 'message': 'Accounts configured'}
            }
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="Prerequisites validation failed"):
            orchestrator._validate_prerequisites()
        
        assert orchestrator.deployment_state['prerequisites_validated'] is False
    
    def test_generate_manifest_success(self, orchestrator, mock_manifest):
        """Test successful manifest generation."""
        orchestrator.manifest_generator.generate_manifest = Mock(return_value=mock_manifest)
        
        result = orchestrator._generate_manifest()
        
        assert result == mock_manifest
        assert orchestrator.deployment_state['manifest_generated'] is True
    
    def test_generate_manifest_failure(self, orchestrator):
        """Test manifest generation failure."""
        orchestrator.manifest_generator.generate_manifest = Mock(
            side_effect=ManifestValidationError("Invalid configuration")
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="Manifest generation failed"):
            orchestrator._generate_manifest()
        
        assert orchestrator.deployment_state['manifest_generated'] is False
    
    def test_deploy_control_tower_success(self, orchestrator, mock_manifest):
        """Test successful Control Tower deployment."""
        orchestrator.control_tower_deployer.create_landing_zone = Mock(return_value='op-12345')
        orchestrator.control_tower_deployer.wait_for_deployment_completion = Mock(return_value=True)
        
        operation_id, landing_zone_arn = orchestrator._deploy_control_tower(mock_manifest)
        
        assert operation_id == 'op-12345'
        assert 'landingzone/op-12345' in landing_zone_arn
        assert orchestrator.deployment_state['control_tower_deployed'] is True
    
    def test_deploy_control_tower_failure(self, orchestrator, mock_manifest):
        """Test Control Tower deployment failure."""
        orchestrator.control_tower_deployer.create_landing_zone = Mock(
            side_effect=DeploymentError("Deployment failed")
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="Control Tower deployment failed"):
            orchestrator._deploy_control_tower(mock_manifest)
        
        assert orchestrator.deployment_state['control_tower_deployed'] is False
    
    def test_deploy_scp_policies_success(self, orchestrator):
        """Test successful SCP policy deployment."""
        orchestrator._get_target_ous_for_scp = Mock(return_value=['ou-12345', 'ou-67890'])
        orchestrator.scp_policy_manager.deploy_scp_tier = Mock(
            return_value={'Policy1': 'policy-id-1', 'Policy2': 'policy-id-2'}
        )
        
        result = orchestrator._deploy_scp_policies()
        
        assert len(result) == 2
        assert 'Policy1' in result
        assert orchestrator.deployment_state['scp_policies_deployed'] is True
    
    def test_deploy_scp_policies_no_target_ous(self, orchestrator):
        """Test SCP policy deployment with no target OUs."""
        orchestrator._get_target_ous_for_scp = Mock(return_value=[])
        
        result = orchestrator._deploy_scp_policies()
        
        assert result == {}
        # State should not be updated when no deployment occurs
        assert orchestrator.deployment_state['scp_policies_deployed'] is False
    
    def test_deploy_scp_policies_failure(self, orchestrator):
        """Test SCP policy deployment failure."""
        orchestrator._get_target_ous_for_scp = Mock(return_value=['ou-12345'])
        orchestrator.scp_policy_manager.deploy_scp_tier = Mock(
            side_effect=SCPPolicyError("SCP deployment failed")
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="SCP policy deployment failed"):
            orchestrator._deploy_scp_policies()
        
        assert orchestrator.deployment_state['scp_policies_deployed'] is False
    
    def test_validate_deployment_success(self, orchestrator):
        """Test successful deployment validation."""
        orchestrator.control_tower_deployer.get_landing_zone_details = Mock(
            return_value={
                'status': 'ACTIVE',
                'drift_status': {'status': 'IN_SYNC'}
            }
        )
        
        # Should not raise exception
        orchestrator._validate_deployment('arn:aws:controltower:us-east-1:123456789012:landingzone/test')
        assert orchestrator.deployment_state['deployment_validated'] is True
    
    def test_validate_deployment_inactive_status(self, orchestrator):
        """Test deployment validation with inactive status."""
        orchestrator.control_tower_deployer.get_landing_zone_details = Mock(
            return_value={
                'status': 'FAILED',
                'drift_status': {'status': 'IN_SYNC'}
            }
        )
        
        with pytest.raises(DeploymentOrchestrationError, match="Landing zone is not active"):
            orchestrator._validate_deployment('arn:aws:controltower:us-east-1:123456789012:landingzone/test')
        
        assert orchestrator.deployment_state['deployment_validated'] is False
    
    def test_validate_deployment_with_drift_warning(self, orchestrator):
        """Test deployment validation with drift warning."""
        orchestrator.control_tower_deployer.get_landing_zone_details = Mock(
            return_value={
                'status': 'ACTIVE',
                'drift_status': {'status': 'DRIFTED'}
            }
        )
        
        # Should not raise exception but should print warning
        orchestrator._validate_deployment('arn:aws:controltower:us-east-1:123456789012:landingzone/test')
        assert orchestrator.deployment_state['deployment_validated'] is True
    
    def test_get_target_ous_for_scp_empty(self, orchestrator):
        """Test getting target OUs returns empty list."""
        # Current implementation returns empty list for testing
        result = orchestrator._get_target_ous_for_scp()
        assert result == []
    
    @patch('builtins.print')
    def test_provide_rollback_guidance(self, mock_print, orchestrator):
        """Test rollback guidance provision."""
        deployment_results = {
            'operation_id': 'op-12345',
            'landing_zone_arn': 'arn:aws:controltower:us-east-1:123456789012:landingzone/test',
            'deployed_policies': {'Policy1': 'policy-id-1', 'Policy2': 'policy-id-2'}
        }
        
        # Should not raise exception
        orchestrator._provide_rollback_guidance(deployment_results)
        
        # Verify print was called with guidance
        assert mock_print.called
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        guidance_text = ' '.join(print_calls)
        
        assert 'Rollback Guidance' in guidance_text
        assert 'op-12345' in guidance_text
        assert 'Policy1' in guidance_text
