"""Unit tests for SecurityConfig functionality."""

import unittest
import tempfile
import yaml
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.security_config import SecurityConfig, SecurityConfigError


class TestSecurityConfig(unittest.TestCase):
    """Test SecurityConfig class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test-security-config.yaml"
        
    def tearDown(self):
        """Clean up test fixtures."""
        if self.config_path.exists():
            self.config_path.unlink()
        os.rmdir(self.temp_dir)
    
    def test_default_configuration(self):
        """Test default configuration creation."""
        config = SecurityConfig(self.config_path)
        
        self.assertEqual(config.get_security_tier(), 'standard')
        self.assertTrue(self.config_path.exists())
    
    def test_security_tier_management(self):
        """Test security tier get/set operations."""
        config = SecurityConfig(self.config_path)
        
        # Test valid tier setting
        config.set_security_tier('strict')
        self.assertEqual(config.get_security_tier(), 'strict')
        
        # Test invalid tier setting
        with self.assertRaises(SecurityConfigError):
            config.set_security_tier('invalid')
    
    def test_ou_overrides(self):
        """Test OU-specific security tier overrides."""
        config = SecurityConfig(self.config_path)
        
        # Set OU override
        config.set_ou_override('Sandbox', 'basic')
        self.assertEqual(config.get_ou_override('Sandbox'), 'basic')
        
        # Test effective tier calculation
        self.assertEqual(config.get_effective_tier_for_ou('Sandbox'), 'basic')
        self.assertEqual(config.get_effective_tier_for_ou('Production'), 'standard')
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        config = SecurityConfig(self.config_path)
        
        # Valid configuration should pass
        errors = config.validate_configuration()
        self.assertEqual(len(errors), 0)


if __name__ == '__main__':
    unittest.main()
