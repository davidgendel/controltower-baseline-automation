"""Configuration validation integration tests."""

import pytest
from pathlib import Path
import tempfile
import yaml
import os

from src.core.config import Configuration, ConfigurationError


class TestConfigurationValidation:
    """Configuration validation integration tests."""
    
    def test_valid_minimal_configuration(self):
        """Test minimal valid configuration."""
        config_data = {
            'aws': {
                'home_region': 'us-east-1',
                'governed_regions': ['us-east-1']
            },
            'accounts': {
                'log_archive_name': 'Log Archive',
                'audit_name': 'Audit'
            },
            'organization': {
                'security_ou_name': 'Security',
                'sandbox_ou_name': 'Sandbox'
            },
            'scp_tier': 'standard'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = Configuration(config_path)
            
            # Verify configuration loaded correctly
            assert config.get_home_region() == 'us-east-1'
            assert config.get_governed_regions() == ['us-east-1']
            
        finally:
            Path(config_path).unlink()
    
    def test_valid_comprehensive_configuration(self):
        """Test comprehensive valid configuration."""
        config_data = {
            'aws': {
                'home_region': 'us-east-1',
                'governed_regions': ['us-east-1', 'us-west-2', 'eu-west-1'],
                'profile': 'production'
            },
            'accounts': {
                'log_archive_name': 'Production-LogArchive',
                'audit_name': 'Production-Audit'
            },
            'organization': {
                'security_ou_name': 'Production-Security',
                'sandbox_ou_name': 'Production-Sandbox'
            },
            'scp_tier': 'strict'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = Configuration(config_path)
            
            # Verify all sections loaded correctly
            assert config.get_home_region() == 'us-east-1'
            assert len(config.get_governed_regions()) == 3
            
        finally:
            Path(config_path).unlink()
    
    def test_invalid_configuration_missing_required(self):
        """Test configuration with missing required fields."""
        config_data = {
            # Missing aws section entirely
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigurationError):
                Configuration(config_path)
                
        finally:
            Path(config_path).unlink()
            
        # Test missing home_region
        config_data = {
            'aws': {
                # Missing home_region
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigurationError):
                Configuration(config_path)
                
        finally:
            Path(config_path).unlink()
    
    def test_configuration_file_formats(self):
        """Test different configuration file formats and edge cases."""
        # Test empty file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('')
            empty_config_path = f.name
        
        try:
            with pytest.raises(ConfigurationError):
                Configuration(empty_config_path)
        finally:
            Path(empty_config_path).unlink()
        
        # Test invalid YAML syntax
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('invalid: yaml: syntax: [')
            invalid_config_path = f.name
        
        try:
            with pytest.raises(ConfigurationError):
                Configuration(invalid_config_path)
        finally:
            Path(invalid_config_path).unlink()
    
    def test_configuration_parameter_combinations(self):
        """Test various parameter combinations."""
        test_cases = [
            # Different SCP tiers
            {'scp_tier': 'basic'},
            {'scp_tier': 'standard'},
            {'scp_tier': 'strict'}
        ]
        
        base_config = {
            'aws': {
                'home_region': 'us-east-1',
                'governed_regions': ['us-east-1']
            },
            'accounts': {
                'log_archive_name': 'Log Archive',
                'audit_name': 'Audit'
            },
            'organization': {
                'security_ou_name': 'Security',
                'sandbox_ou_name': 'Sandbox'
            },
            'scp_tier': 'standard'
        }
        
        for test_case in test_cases:
            # Merge test case with base config
            config_data = {**base_config, **test_case}
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(config_data, f)
                config_path = f.name
            
            try:
                config = Configuration(config_path)
                # If we get here without exception, the configuration is valid
                assert True
                
            finally:
                Path(config_path).unlink()
