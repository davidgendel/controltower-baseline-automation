"""Unit tests for documentation generator."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

from src.documentation.generator import DocumentationGenerator, DocumentationError
from src.core.config import Configuration
from src.core.aws_client import AWSClientManager


@pytest.fixture
def mock_config():
    config = Mock(spec=Configuration)
    config.get_home_region.return_value = 'us-east-1'
    config.get_governed_regions.return_value = ['us-east-1', 'us-west-2']
    config.get_scp_tier.return_value = 'standard'
    return config


@pytest.fixture
def mock_aws_client():
    client = Mock(spec=AWSClientManager)
    client.account_id = '123456789012'
    return client


@pytest.fixture
def doc_generator(mock_config, mock_aws_client):
    return DocumentationGenerator(mock_config, mock_aws_client)


class TestDocumentationGenerator:
    
    def test_generate_deployment_summary_success(self, doc_generator):
        """Test successful deployment summary generation."""
        deployment_state = {
            'control_tower': {'status': 'success'},
            'security_baseline': {'status': 'success'}
        }
        
        result = doc_generator.generate_deployment_summary(deployment_state)
        
        assert '# AWS Control Tower Deployment Summary' in result
        assert '123456789012' in result
        assert 'us-east-1' in result
        assert 'standard' in result
        assert '✅ success' in result
    
    def test_generate_deployment_summary_with_failures(self, doc_generator):
        """Test deployment summary generation with failures."""
        deployment_state = {
            'control_tower': {'status': 'success'},
            'security_baseline': {'status': 'failed'}
        }
        
        result = doc_generator.generate_deployment_summary(deployment_state)
        
        assert '✅ success' in result
        assert '❌ failed' in result
    
    def test_generate_deployment_summary_error(self, doc_generator):
        """Test deployment summary generation error handling."""
        with patch.object(doc_generator.config, 'get_home_region', side_effect=Exception("Config error")):
            with pytest.raises(DocumentationError, match="Failed to generate deployment summary"):
                doc_generator.generate_deployment_summary({})
    
    def test_generate_configuration_docs_success(self, doc_generator):
        """Test successful configuration documentation generation."""
        result = doc_generator.generate_configuration_docs()
        
        assert '# Configuration Reference' in result
        assert 'aws.home_region' in result
        assert 'scp_tier' in result
        assert '```yaml' in result
        assert 'Validation Rules' in result
    
    def test_generate_validation_report_success(self, doc_generator):
        """Test successful validation report generation."""
        validation_results = {
            'overall_healthy': True,
            'config': {
                'overall_healthy': True,
                'delegated_admin': True,
                'aggregator': True
            },
            'guardduty': {
                'overall_healthy': False,
                'delegated_admin': True,
                'detector_enabled': False
            }
        }
        
        result = doc_generator.generate_validation_report(validation_results)
        
        assert '# Deployment Validation Report' in result
        assert '✅ PASSED' in result
        assert 'Config ✅' in result
        assert 'Guardduty ❌' in result
        assert 'Delegated Admin**: ✅' in result
        assert 'Detector Enabled**: ❌' in result
    
    def test_generate_validation_report_overall_failure(self, doc_generator):
        """Test validation report generation with overall failure."""
        validation_results = {
            'overall_healthy': False,
            'config': {'overall_healthy': False, 'delegated_admin': False}
        }
        
        result = doc_generator.generate_validation_report(validation_results)
        
        assert '❌ FAILED' in result
        assert 'Review failed checks' in result
    
    def test_generate_validation_report_error(self, doc_generator):
        """Test validation report generation error handling."""
        with patch('src.documentation.generator.datetime') as mock_datetime:
            mock_datetime.now.side_effect = Exception("Time error")
            
            with pytest.raises(DocumentationError, match="Failed to generate validation report"):
                doc_generator.generate_validation_report({})
    
    def test_save_documentation_success(self, doc_generator):
        """Test successful documentation save."""
        content = "# Test Documentation"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            result_path = doc_generator.save_documentation(content, "test.md", output_dir)
            
            assert result_path.exists()
            assert result_path.read_text() == content
            assert result_path.name == "test.md"
    
    def test_save_documentation_default_dir(self, doc_generator):
        """Test documentation save with default directory."""
        content = "# Test Documentation"
        
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.write_text') as mock_write:
            
            result_path = doc_generator.save_documentation(content, "test.md")
            
            mock_mkdir.assert_called_once_with(exist_ok=True)
            mock_write.assert_called_once_with(content, encoding='utf-8')
            assert str(result_path) == "docs/test.md"
    
    def test_save_documentation_error(self, doc_generator):
        """Test documentation save error handling."""
        content = "# Test Documentation"
        
        with patch('pathlib.Path.write_text', side_effect=Exception("Write error")):
            with pytest.raises(DocumentationError, match="Failed to save documentation"):
                doc_generator.save_documentation(content, "test.md")
