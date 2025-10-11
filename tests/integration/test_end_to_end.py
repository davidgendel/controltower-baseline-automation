"""End-to-end integration tests for Control Tower automation."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import yaml

from src.core.config import Configuration
from src.core.aws_client import AWSClientManager
from src.documentation.generator import DocumentationGenerator
from src.documentation.diagrams import DiagramGenerator
from src.documentation.validator import DeploymentValidator


@pytest.fixture
def test_config():
    """Create test configuration."""
    config_data = {
        'aws': {
            'home_region': 'us-east-1',
            'governed_regions': ['us-east-1', 'us-west-2']
        },
        'accounts': {
            'log_archive_name': 'Log Archive',
            'audit_name': 'Audit'
        },
        'organization': {
            'security_ou_name': 'Security',
            'sandbox_ou_name': 'Sandbox'
        },
        'scp_tier': 'standard',
        'post_deployment': {
            'guardduty': {
                'enabled': True,
                'delegated_admin_account': 'audit'
            },
            'security_hub': {
                'enabled': True,
                'delegated_admin_account': 'audit'
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        config = Configuration(config_path)
        return config
    finally:
        Path(config_path).unlink()


@pytest.fixture
def mock_aws_client():
    """Create mock AWS client manager."""
    client = Mock(spec=AWSClientManager)
    client.account_id = '123456789012'  # Add account_id attribute
    
    # Mock Control Tower client
    mock_ct_client = MagicMock()
    mock_ct_client.get_landing_zone.return_value = {
        'status': 'ACTIVE',
        'driftStatus': 'DRIFTED'
    }
    
    # Mock Organizations client
    mock_org_client = MagicMock()
    mock_org_client.list_roots.return_value = {
        'Roots': [{'Id': 'r-123456'}]
    }
    mock_org_client.list_accounts.return_value = {
        'Accounts': [
            {'Id': '123456789012', 'Name': 'Management'},
            {'Id': '123456789013', 'Name': 'Log Archive'},
            {'Id': '123456789014', 'Name': 'Audit'}
        ]
    }
    
    # Mock security service clients
    mock_config_client = MagicMock()
    mock_config_client.describe_configuration_aggregators.return_value = {
        'ConfigurationAggregators': [{'AggregatorName': 'test-aggregator'}]
    }
    
    mock_gd_client = MagicMock()
    mock_gd_client.list_detectors.return_value = {
        'DetectorIds': ['detector-123']
    }
    
    mock_sh_client = MagicMock()
    mock_sh_client.describe_hub.return_value = {
        'HubArn': 'arn:aws:securityhub:us-east-1:123456789012:hub/default'
    }
    
    # Configure client factory
    client.get_client.side_effect = lambda service: {
        'controltower': mock_ct_client,
        'organizations': mock_org_client,
        'config': mock_config_client,
        'guardduty': mock_gd_client,
        'securityhub': mock_sh_client
    }.get(service, MagicMock())
    
    return client


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    def test_complete_documentation_workflow(self, test_config, mock_aws_client):
        """Test complete documentation generation workflow."""
        # Initialize components
        doc_generator = DocumentationGenerator(test_config, mock_aws_client)
        validator = DeploymentValidator(test_config, mock_aws_client)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Generate deployment summary
            deployment_state = {
                'control_tower': {'status': 'ACTIVE'},
                'security_baseline': {'status': 'CONFIGURED'},
                'timestamp': '2024-01-01T00:00:00Z'
            }
            
            summary = doc_generator.generate_deployment_summary(deployment_state)
            assert 'Control Tower Deployment Summary' in summary
            assert 'ACTIVE' in summary
            
            # Generate configuration documentation
            config_docs = doc_generator.generate_configuration_docs()
            assert 'Configuration Reference' in config_docs
            assert 'us-east-1' in config_docs
            
            # Generate validation report
            validation_results = validator.generate_validation_report()
            validation_report = doc_generator.generate_validation_report(validation_results)
            assert 'Validation Report' in validation_report
            
            # Save all documentation
            summary_path = doc_generator.save_documentation(
                summary, 'deployment_summary.md', output_dir
            )
            config_path = doc_generator.save_documentation(
                config_docs, 'configuration.md', output_dir
            )
            validation_path = doc_generator.save_documentation(
                validation_report, 'validation_report.md', output_dir
            )
            
            # Verify files were created
            assert summary_path.exists()
            assert config_path.exists()
            assert validation_path.exists()
    
    def test_complete_diagram_workflow(self, test_config, mock_aws_client):
        """Test complete diagram generation workflow."""
        diagram_generator = DiagramGenerator(test_config, mock_aws_client)
        
        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.dict('sys.modules', {
                 'diagrams': MagicMock(),
                 'diagrams.aws': MagicMock(),
                 'diagrams.aws.management': MagicMock(),
                 'diagrams.aws.security': MagicMock(),
                 'diagrams.aws.storage': MagicMock(),
                 'diagrams.aws.general': MagicMock()
             }):
            
            output_dir = Path(temp_dir)
            
            # Generate all diagrams
            diagram_paths = diagram_generator.generate_all_diagrams(output_dir)
            
            # Verify all diagrams were generated
            assert len(diagram_paths) == 3
            expected_files = [
                'control_tower_architecture.png',
                'security_topology.png',
                'organization_structure.png'
            ]
            
            for expected_file in expected_files:
                expected_path = output_dir / expected_file
                assert expected_path in diagram_paths
    
    def test_complete_validation_workflow(self, test_config, mock_aws_client):
        """Test complete validation workflow."""
        validator = DeploymentValidator(test_config, mock_aws_client)
        
        # Run all validation checks
        ct_validation = validator.validate_control_tower_deployment()
        sb_validation = validator.validate_security_baseline()
        ae_validation = validator.validate_account_enrollment()
        
        # Verify validation results
        assert ct_validation['status'] == 'PASS'
        assert sb_validation['status'] == 'PASS'
        assert ae_validation['status'] == 'PASS'
        
        # Generate comprehensive report
        full_report = validator.generate_validation_report()
        
        assert full_report['overall_status'] == 'PASS'
        assert full_report['summary']['passed_checks'] == 3
        assert full_report['summary']['failed_checks'] == 0
    
    def test_error_handling_workflow(self, test_config):
        """Test error handling across components."""
        # Create mock client that raises errors
        mock_aws_client = Mock(spec=AWSClientManager)
        mock_aws_client.account_id = '123456789012'
        mock_aws_client.get_client.side_effect = Exception("AWS API Error")
        
        validator = DeploymentValidator(test_config, mock_aws_client)
        
        # Validation should handle errors gracefully and not raise ValidationError
        # Instead, it should return FAIL status with remediation steps
        ct_validation = validator.validate_control_tower_deployment()
        assert ct_validation['status'] == 'FAIL'
        assert len(ct_validation['remediation_steps']) > 0
        
        sb_validation = validator.validate_security_baseline()
        assert sb_validation['status'] == 'FAIL'
        
        # Full report should aggregate errors
        full_report = validator.generate_validation_report()
        assert full_report['overall_status'] == 'FAIL'
        assert full_report['summary']['failed_checks'] > 0
    
    def test_configuration_integration(self, test_config):
        """Test configuration integration across components."""
        mock_aws_client = Mock(spec=AWSClientManager)
        
        # Initialize all components with same configuration
        doc_generator = DocumentationGenerator(test_config, mock_aws_client)
        diagram_generator = DiagramGenerator(test_config, mock_aws_client)
        validator = DeploymentValidator(test_config, mock_aws_client)
        
        # Verify configuration is properly shared
        assert doc_generator.config == test_config
        assert diagram_generator.config == test_config
        assert validator.config == test_config
        
        # Verify AWS client is properly shared
        assert doc_generator.aws_client == mock_aws_client
        assert diagram_generator.aws_client == mock_aws_client
        assert validator.aws_client == mock_aws_client
    
    def test_performance_workflow(self, test_config, mock_aws_client):
        """Test performance of complete workflow."""
        import time
        
        start_time = time.time()
        
        # Run complete workflow
        validator = DeploymentValidator(test_config, mock_aws_client)
        doc_generator = DocumentationGenerator(test_config, mock_aws_client)
        
        # Generate validation report
        validation_results = validator.generate_validation_report()
        
        # Generate documentation
        deployment_state = {'status': 'ACTIVE'}
        summary = doc_generator.generate_deployment_summary(deployment_state)
        config_docs = doc_generator.generate_configuration_docs()
        validation_report = doc_generator.generate_validation_report(validation_results)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify reasonable performance (should complete within 5 seconds)
        assert execution_time < 5.0
        
        # Verify all outputs were generated
        assert len(summary) > 0
        assert len(config_docs) > 0
        assert len(validation_report) > 0
