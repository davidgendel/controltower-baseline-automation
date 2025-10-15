"""Security configuration management for Control Tower deployment.

This module provides independent security policy configuration management,
decoupled from deployment scope templates to allow flexible security
tier selection and policy customization.
"""

from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import yaml
import logging

from src.core.config import Configuration


logger = logging.getLogger(__name__)


class SecurityConfigError(Exception):
    """Raised when security configuration operations fail."""
    pass


class SecurityConfig:
    """Manages security configuration independently from deployment templates.
    
    This class provides decoupled security policy management, allowing
    organizations to select and customize security tiers independently
    from their organizational structure templates.
    """
    
    # Available security tiers
    SECURITY_TIERS = {
        'basic': {
            'name': 'Basic Security Tier',
            'description': 'Minimal restrictions for development environments',
            'policies': ['deny_root_access', 'require_mfa']
        },
        'standard': {
            'name': 'Standard Security Tier', 
            'description': 'Balanced security for production workloads',
            'policies': ['deny_root_access', 'require_mfa', 'restrict_regions', 'deny_leave_org']
        },
        'strict': {
            'name': 'Strict Security Tier',
            'description': 'Maximum security for compliance environments',
            'policies': ['deny_root_access', 'require_mfa', 'restrict_regions', 'deny_leave_org', 
                        'restrict_instance_types', 'require_encryption']
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize security configuration.
        
        Args:
            config_path: Optional path to security configuration file
        """
        self.config_path = config_path or Path("config/security-config.yaml")
        self._config_data = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load security configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self._config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded security configuration from {self.config_path}")
            else:
                # Create default configuration
                self._config_data = self._get_default_config()
                self.save_config()
                logger.info(f"Created default security configuration at {self.config_path}")
        except Exception as e:
            raise SecurityConfigError(f"Failed to load security configuration: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default security configuration."""
        return {
            'security_tier': 'standard',
            'custom_policies': {},
            'ou_overrides': {},
            'account_exceptions': []
        }
    
    def get_security_tier(self) -> str:
        """Get current security tier.
        
        Returns:
            Security tier name (basic, standard, strict)
        """
        return self._config_data.get('security_tier', 'standard')
    
    def set_security_tier(self, tier: str) -> None:
        """Set security tier.
        
        Args:
            tier: Security tier name (basic, standard, strict)
            
        Raises:
            SecurityConfigError: If tier is invalid
        """
        if tier not in self.SECURITY_TIERS:
            raise SecurityConfigError(f"Invalid security tier: {tier}. Must be one of: {list(self.SECURITY_TIERS.keys())}")
        
        self._config_data['security_tier'] = tier
        logger.info(f"Security tier set to: {tier}")
    
    def get_tier_policies(self, tier: Optional[str] = None) -> List[str]:
        """Get policies for a security tier.
        
        Args:
            tier: Security tier name, defaults to current tier
            
        Returns:
            List of policy names for the tier
        """
        tier = tier or self.get_security_tier()
        return self.SECURITY_TIERS.get(tier, {}).get('policies', [])
    
    def get_ou_override(self, ou_name: str) -> Optional[str]:
        """Get security tier override for specific OU.
        
        Args:
            ou_name: Organizational Unit name
            
        Returns:
            Override security tier or None if no override
        """
        return self._config_data.get('ou_overrides', {}).get(ou_name)
    
    def set_ou_override(self, ou_name: str, tier: str) -> None:
        """Set security tier override for specific OU.
        
        Args:
            ou_name: Organizational Unit name
            tier: Security tier for this OU
            
        Raises:
            SecurityConfigError: If tier is invalid
        """
        if tier not in self.SECURITY_TIERS:
            raise SecurityConfigError(f"Invalid security tier: {tier}")
        
        if 'ou_overrides' not in self._config_data:
            self._config_data['ou_overrides'] = {}
        
        self._config_data['ou_overrides'][ou_name] = tier
        logger.info(f"Set OU override: {ou_name} -> {tier}")
    
    def add_account_exception(self, account_id: str, reason: str) -> None:
        """Add account exception from security policies.
        
        Args:
            account_id: AWS account ID
            reason: Reason for exception
        """
        if 'account_exceptions' not in self._config_data:
            self._config_data['account_exceptions'] = []
        
        exception = {'account_id': account_id, 'reason': reason}
        if exception not in self._config_data['account_exceptions']:
            self._config_data['account_exceptions'].append(exception)
            logger.info(f"Added account exception: {account_id} - {reason}")
    
    def save_config(self) -> None:
        """Save security configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config_data, f, default_flow_style=False, sort_keys=True)
            logger.info(f"Security configuration saved to {self.config_path}")
        except Exception as e:
            raise SecurityConfigError(f"Failed to save security configuration: {e}")
    
    def get_effective_tier_for_ou(self, ou_name: str) -> str:
        """Get effective security tier for an OU (considering overrides).
        
        Args:
            ou_name: Organizational Unit name
            
        Returns:
            Effective security tier for the OU
        """
        override = self.get_ou_override(ou_name)
        return override if override else self.get_security_tier()
    
    def validate_configuration(self) -> List[str]:
        """Validate security configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate security tier
        tier = self.get_security_tier()
        if tier not in self.SECURITY_TIERS:
            errors.append(f"Invalid security tier: {tier}")
        
        # Validate OU overrides
        for ou_name, override_tier in self._config_data.get('ou_overrides', {}).items():
            if override_tier not in self.SECURITY_TIERS:
                errors.append(f"Invalid override tier for OU {ou_name}: {override_tier}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary.
        
        Returns:
            Security configuration dictionary
        """
        return self._config_data.copy()


def migrate_legacy_config(base_config: Configuration) -> SecurityConfig:
    """Migrate legacy scp_tier from base configuration to SecurityConfig.
    
    Args:
        base_config: Base configuration instance
        
    Returns:
        SecurityConfig instance with migrated settings
    """
    security_config = SecurityConfig()
    
    # Migrate scp_tier if present
    if hasattr(base_config, 'get_scp_tier'):
        legacy_tier = base_config.get_scp_tier()
        security_config.set_security_tier(legacy_tier)
        security_config.save_config()
        logger.info(f"Migrated legacy scp_tier '{legacy_tier}' to SecurityConfig")
    
    return security_config
