"""Unit tests for post-deployment orchestrator."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.post_deployment.orchestrator import PostDeploymentOrchestrator, PostDeploymentOrchestrationError
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
def orchestrator(mock_config, mock_aws_client):
    return PostDeploymentOrchestrator(mock_config, mock_aws_client)


class TestPostDeploymentOrchestrator:
    
    @patch('src.post_deployment.orchestrator.ConfigOrganizationManager')
    @patch('src.post_deployment.orchestrator.GuardDutyOrganizationManager')
    @patch('src.post_deployment.orchestrator.SecurityHubOrganizationManager')
    def test_orchestrate_security_baseline_success(self, mock_security_hub, mock_guardduty, mock_config, orchestrator):
        """Test successful security baseline orchestration."""
        # Mock Config manager
        mock_config_instance = Mock()
        mock_config_instance.enable_delegated_administrator.return_value = True
        mock_config_instance.create_organization_aggregator.return_value = {'ConfigurationAggregatorName': 'test'}
        mock_config.return_value = mock_config_instance
        
        # Mock GuardDuty manager
        mock_guardduty_instance = Mock()
        mock_guardduty_instance.enable_delegated_administrator.return_value = True
        mock_guardduty_instance.enable_organization_guardduty.return_value = {'detector_id': 'test', 'auto_enable': True}
        mock_guardduty_instance.set_finding_frequency.return_value = True
        mock_guardduty.return_value = mock_guardduty_instance
        
        # Mock Security Hub manager
        mock_security_hub_instance = Mock()
        mock_security_hub_instance.enable_delegated_administrator.return_value = True
        mock_security_hub_instance.enable_organization_security_hub.return_value = {'auto_enable': True}
        mock_security_hub_instance.enable_foundational_standards.return_value = [{'StandardsArn': 'test'}]
        mock_security_hub.return_value = mock_security_hub_instance
        
        # Create new orchestrator with mocked managers
        orchestrator = PostDeploymentOrchestrator(Mock(), Mock())
        orchestrator.config_manager = mock_config_instance
        orchestrator.guardduty_manager = mock_guardduty_instance
        orchestrator.security_hub_manager = mock_security_hub_instance
        
        result = orchestrator.orchestrate_security_baseline('123456789012')
        
        assert result['overall_status'] == 'success'
        assert result['config']['status'] == 'success'
        assert result['guardduty']['status'] == 'success'
        assert result['security_hub']['status'] == 'success'
        
        # Verify all managers were called
        mock_config_instance.enable_delegated_administrator.assert_called_once_with('123456789012')
        mock_guardduty_instance.enable_delegated_administrator.assert_called_once_with('123456789012')
        mock_security_hub_instance.enable_delegated_administrator.assert_called_once_with('123456789012')
    
    @patch('src.post_deployment.orchestrator.ConfigOrganizationManager')
    def test_orchestrate_security_baseline_config_failure(self, mock_config, orchestrator):
        """Test security baseline orchestration with Config failure."""
        mock_config_instance = Mock()
        mock_config_instance.enable_delegated_administrator.side_effect = Exception("Config failed")
        mock_config.return_value = mock_config_instance
        
        orchestrator = PostDeploymentOrchestrator(Mock(), Mock())
        orchestrator.config_manager = mock_config_instance
        
        with pytest.raises(PostDeploymentOrchestrationError, match="Orchestration failed"):
            orchestrator.orchestrate_security_baseline('123456789012')
    
    def test_validate_service_health_all_healthy(self, orchestrator):
        """Test service health validation when all services are healthy."""
        with patch.object(orchestrator.config_manager, 'validate_config_setup') as mock_config, \
             patch.object(orchestrator.guardduty_manager, 'validate_guardduty_setup') as mock_guardduty, \
             patch.object(orchestrator.security_hub_manager, 'validate_security_hub_setup') as mock_security_hub:
            
            mock_config.return_value = {
                'delegated_admin': True,
                'aggregator': True,
                'service_access': True
            }
            mock_guardduty.return_value = {
                'delegated_admin': True,
                'detector_enabled': True,
                'organization_config': True,
                'service_access': True
            }
            mock_security_hub.return_value = {
                'delegated_admin': True,
                'security_hub_enabled': True,
                'organization_config': True,
                'standards_enabled': True,
                'service_access': True
            }
            
            result = orchestrator.validate_service_health()
            
            assert result['overall_healthy'] is True
            assert result['config']['overall_healthy'] is True
            assert result['guardduty']['overall_healthy'] is True
            assert result['security_hub']['overall_healthy'] is True
    
    def test_validate_service_health_some_unhealthy(self, orchestrator):
        """Test service health validation when some services are unhealthy."""
        with patch.object(orchestrator.config_manager, 'validate_config_setup') as mock_config, \
             patch.object(orchestrator.guardduty_manager, 'validate_guardduty_setup') as mock_guardduty, \
             patch.object(orchestrator.security_hub_manager, 'validate_security_hub_setup') as mock_security_hub:
            
            mock_config.return_value = {
                'delegated_admin': True,
                'aggregator': False,  # Unhealthy
                'service_access': True
            }
            mock_guardduty.return_value = {
                'delegated_admin': True,
                'detector_enabled': True,
                'organization_config': True,
                'service_access': True
            }
            mock_security_hub.return_value = {
                'delegated_admin': True,
                'security_hub_enabled': True,
                'organization_config': True,
                'standards_enabled': True,
                'service_access': True
            }
            
            result = orchestrator.validate_service_health()
            
            assert result['overall_healthy'] is False
            assert result['config']['overall_healthy'] is False
            assert result['guardduty']['overall_healthy'] is True
            assert result['security_hub']['overall_healthy'] is True
    
    def test_get_deployment_status_complete(self, orchestrator):
        """Test deployment status when all services are deployed."""
        orchestrator.validate_service_health = Mock(return_value={
            'config': {'delegated_admin': True, 'aggregator': True, 'overall_healthy': True},
            'guardduty': {'delegated_admin': True, 'detector_enabled': True, 'overall_healthy': True},
            'security_hub': {'delegated_admin': True, 'security_hub_enabled': True, 'overall_healthy': True},
            'overall_healthy': True
        })
        
        result = orchestrator.get_deployment_status()
        
        assert result['summary']['total_services'] == 3
        assert result['summary']['healthy_services'] == 3
        assert result['summary']['failed_services'] == 0
        assert result['summary']['deployment_complete'] is True
        assert result['services']['config']['healthy'] is True
        assert result['services']['guardduty']['healthy'] is True
        assert result['services']['security_hub']['healthy'] is True
    
    def test_get_deployment_status_partial(self, orchestrator):
        """Test deployment status when some services failed."""
        orchestrator.validate_service_health = Mock(return_value={
            'config': {'delegated_admin': True, 'aggregator': False, 'overall_healthy': False},
            'guardduty': {'delegated_admin': True, 'detector_enabled': True, 'overall_healthy': True},
            'security_hub': {'delegated_admin': False, 'security_hub_enabled': False, 'overall_healthy': False},
            'overall_healthy': False
        })
        
        result = orchestrator.get_deployment_status()
        
        assert result['summary']['total_services'] == 3
        assert result['summary']['healthy_services'] == 1
        assert result['summary']['failed_services'] == 2
        assert result['summary']['deployment_complete'] is False
        assert result['services']['config']['healthy'] is False
        assert result['services']['guardduty']['healthy'] is True
        assert result['services']['security_hub']['healthy'] is False
