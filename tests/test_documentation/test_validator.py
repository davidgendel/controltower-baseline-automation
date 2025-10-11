"""Unit tests for deployment validator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.documentation.validator import DeploymentValidator, ValidationError
from src.core.config import Configuration
from src.core.aws_client import AWSClientManager


@pytest.fixture
def mock_config():
    config = Mock(spec=Configuration)
    config.get_home_region.return_value = 'us-east-1'
    return config


@pytest.fixture
def mock_aws_client():
    client = Mock(spec=AWSClientManager)
    return client


@pytest.fixture
def validator(mock_config, mock_aws_client):
    return DeploymentValidator(mock_config, mock_aws_client)


class TestDeploymentValidator:
    
    def test_validate_control_tower_deployment_success(self, validator):
        """Test successful Control Tower deployment validation."""
        mock_ct_client = MagicMock()
        mock_org_client = MagicMock()
        
        # Mock Control Tower response
        mock_ct_client.get_landing_zone.return_value = {
            'status': 'ACTIVE',
            'driftStatus': 'DRIFTED'
        }
        
        # Mock Organizations response
        mock_org_client.list_roots.return_value = {
            'Roots': [{'Id': 'r-123456'}]
        }
        mock_org_client.list_organizational_units_for_parent.return_value = {
            'OrganizationalUnits': [
                {'Name': 'Security'},
                {'Name': 'Sandbox'}
            ]
        }
        
        validator.aws_client.get_client.side_effect = lambda service: {
            'controltower': mock_ct_client,
            'organizations': mock_org_client
        }[service]
        
        result = validator.validate_control_tower_deployment()
        
        assert result['status'] == 'PASS'
        assert result['landing_zone_status'] == 'ACTIVE'
        assert result['drift_status'] == 'DRIFTED'
        assert 'Security' in result['organizational_units']
        assert 'Sandbox' in result['organizational_units']
    
    def test_validate_control_tower_deployment_failure(self, validator):
        """Test Control Tower deployment validation failure."""
        mock_ct_client = MagicMock()
        mock_ct_client.get_landing_zone.side_effect = Exception("Access denied")
        
        validator.aws_client.get_client.return_value = mock_ct_client
        
        result = validator.validate_control_tower_deployment()
        
        assert result['status'] == 'FAIL'
        assert len(result['remediation_steps']) > 0
        assert 'Cannot access Control Tower' in result['remediation_steps'][0]
    
    def test_validate_security_baseline_success(self, validator):
        """Test successful security baseline validation."""
        mock_config_client = MagicMock()
        mock_gd_client = MagicMock()
        mock_sh_client = MagicMock()
        
        # Mock service responses
        mock_config_client.describe_configuration_aggregators.return_value = {
            'ConfigurationAggregators': [{'AggregatorName': 'test-aggregator'}]
        }
        mock_gd_client.list_detectors.return_value = {
            'DetectorIds': ['detector-123']
        }
        mock_sh_client.describe_hub.return_value = {
            'HubArn': 'arn:aws:securityhub:us-east-1:123456789012:hub/default'
        }
        
        validator.aws_client.get_client.side_effect = lambda service: {
            'config': mock_config_client,
            'guardduty': mock_gd_client,
            'securityhub': mock_sh_client
        }[service]
        
        result = validator.validate_security_baseline()
        
        assert result['status'] == 'PASS'
        assert result['config_status'] == 'ACTIVE'
        assert result['guardduty_status'] == 'ACTIVE'
        assert result['security_hub_status'] == 'ACTIVE'
    
    def test_validate_security_baseline_partial_failure(self, validator):
        """Test security baseline validation with partial failures."""
        mock_config_client = MagicMock()
        mock_gd_client = MagicMock()
        mock_sh_client = MagicMock()
        
        # Mock mixed responses
        mock_config_client.describe_configuration_aggregators.return_value = {
            'ConfigurationAggregators': []
        }
        mock_gd_client.list_detectors.return_value = {
            'DetectorIds': ['detector-123']
        }
        mock_sh_client.describe_hub.side_effect = Exception("Not enabled")
        
        validator.aws_client.get_client.side_effect = lambda service: {
            'config': mock_config_client,
            'guardduty': mock_gd_client,
            'securityhub': mock_sh_client
        }[service]
        
        result = validator.validate_security_baseline()
        
        assert result['status'] == 'FAIL'
        assert result['config_status'] == 'MISSING'
        assert result['guardduty_status'] == 'ACTIVE'
        assert result['security_hub_status'] == 'ERROR'
        assert len(result['remediation_steps']) > 0
    
    def test_validate_account_enrollment_success(self, validator):
        """Test successful account enrollment validation."""
        mock_org_client = MagicMock()
        mock_ct_client = MagicMock()
        
        # Mock organization accounts
        mock_org_client.list_accounts.return_value = {
            'Accounts': [
                {'Id': '123456789012', 'Name': 'Management'},
                {'Id': '123456789013', 'Name': 'Log Archive'},
                {'Id': '123456789014', 'Name': 'Audit'}
            ]
        }
        
        validator.aws_client.get_client.side_effect = lambda service: {
            'organizations': mock_org_client,
            'controltower': mock_ct_client
        }[service]
        
        result = validator.validate_account_enrollment()
        
        assert result['status'] == 'PASS'
        assert result['total_accounts'] == 3
        assert result['compliance_status'] == 'COMPLIANT'
        assert len(result['enrolled_accounts']) == 3
    
    def test_validate_account_enrollment_error(self, validator):
        """Test account enrollment validation with error."""
        mock_org_client = MagicMock()
        mock_org_client.list_accounts.side_effect = Exception("Access denied")
        
        validator.aws_client.get_client.return_value = mock_org_client
        
        result = validator.validate_account_enrollment()
        
        assert result['status'] == 'FAIL'
        assert len(result['remediation_steps']) > 0
    
    def test_generate_validation_report_success(self, validator):
        """Test successful validation report generation."""
        with patch.object(validator, 'validate_control_tower_deployment') as mock_ct, \
             patch.object(validator, 'validate_security_baseline') as mock_sb, \
             patch.object(validator, 'validate_account_enrollment') as mock_ae:
            
            # Mock all validations as passing
            mock_ct.return_value = {'status': 'PASS'}
            mock_sb.return_value = {'status': 'PASS'}
            mock_ae.return_value = {'status': 'PASS'}
            
            result = validator.generate_validation_report()
            
            assert result['overall_status'] == 'PASS'
            assert result['summary']['passed_checks'] == 3
            assert result['summary']['failed_checks'] == 0
            assert result['summary']['remediation_required'] is False
            assert 'timestamp' in result
    
    def test_generate_validation_report_with_failures(self, validator):
        """Test validation report generation with failures."""
        with patch.object(validator, 'validate_control_tower_deployment') as mock_ct, \
             patch.object(validator, 'validate_security_baseline') as mock_sb, \
             patch.object(validator, 'validate_account_enrollment') as mock_ae:
            
            # Mock mixed validation results
            mock_ct.return_value = {'status': 'PASS'}
            mock_sb.return_value = {'status': 'FAIL'}
            mock_ae.return_value = {'status': 'FAIL'}
            
            result = validator.generate_validation_report()
            
            assert result['overall_status'] == 'FAIL'
            assert result['summary']['passed_checks'] == 1
            assert result['summary']['failed_checks'] == 2
            assert result['summary']['remediation_required'] is True
    
    def test_validation_error_handling(self, validator):
        """Test validation error handling."""
        with patch.object(validator, 'validate_control_tower_deployment', 
                         side_effect=Exception("Validation failed")):
            
            with pytest.raises(ValidationError, match="Validation report generation failed"):
                validator.generate_validation_report()
