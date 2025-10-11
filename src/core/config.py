"""Configuration management for AWS Control Tower automation.

This module handles YAML configuration loading, validation, and
environment variable override support following AWS Control Tower
launch parameter requirements.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class Configuration:
    """Configuration management with YAML loading and validation.

    This class handles loading configuration from YAML files,
    validating the structure, and supporting environment variable
    overrides following AWS Control Tower requirements.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize configuration manager.

        Args:
            config_path: Optional path to configuration file.
                        If None, auto-detects config.yaml in current directory.

        Raises:
            ConfigurationError: When configuration file is invalid
        """
        self._config: Dict[str, Any] = {}
        self._config_path = self._resolve_config_path(config_path)
        self._load_configuration()
        self._apply_environment_overrides()
        self._validate_configuration()

    def _resolve_config_path(self, config_path: Optional[str]) -> Path:
        """Resolve configuration file path.

        Args:
            config_path: Optional path to configuration file

        Returns:
            Resolved Path object to configuration file

        Raises:
            ConfigurationError: When configuration file not found
        """
        if config_path:
            path = Path(config_path)
        else:
            # Auto-detect config.yaml in current directory
            path = Path("config.yaml")
            if not path.exists():
                path = Path("config/settings.yaml")

        if not path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {path}. "
                "Please create a configuration file or specify a valid path."
            )

        return path

    def _load_configuration(self) -> None:
        """Load configuration from YAML file.

        Raises:
            ConfigurationError: When YAML file is invalid
        """
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration file {self._config_path}: {e}"
            )
        except IOError as e:
            raise ConfigurationError(
                f"Unable to read configuration file {self._config_path}: {e}"
            )

    def _validate_configuration(self) -> None:
        """Validate configuration has required fields.
        
        Raises:
            ConfigurationError: When required fields are missing
        """
        # Only validate AWS section as required - accounts section is optional
        if 'aws' not in self._config:
            raise ConfigurationError("Required configuration section 'aws' is missing")
            
        aws_config = self._config['aws']
        
        # Validate required AWS fields
        if 'home_region' not in aws_config:
            raise ConfigurationError("Required field 'aws.home_region' is missing")

        # Validate home region format
        home_region = aws_config["home_region"]
        if not isinstance(home_region, str) or not home_region:
            raise ConfigurationError("Field 'aws.home_region' must be a non-empty string")

        # Validate governed regions if present
        if 'governed_regions' in aws_config:
            governed_regions = aws_config["governed_regions"]
            if not isinstance(governed_regions, list):
                raise ConfigurationError("Field 'aws.governed_regions' must be a list")

            # Ensure home region is in governed regions
            if home_region not in governed_regions:
                governed_regions.insert(0, home_region)
                self._config["aws"]["governed_regions"] = governed_regions

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        # AWS region override
        if "AWS_REGION" in os.environ:
            self._set_nested_value("aws.home_region", os.environ["AWS_REGION"])

        # AWS profile override
        if "AWS_PROFILE" in os.environ:
            self._set_nested_value(
                "aws.profile_name", os.environ["AWS_PROFILE"]
            )

    def _set_nested_value(self, key_path: str, value: Any) -> None:
        """Set nested configuration value using dot notation.

        Args:
            key_path: Dot-separated key path (e.g., 'aws.home_region')
            value: Value to set
        """
        keys = key_path.split(".")
        current = self._config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key_path: Dot-separated key path (e.g., 'aws.home_region')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        current = self._config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def get_aws_config(self) -> Dict[str, Any]:
        """Get AWS-specific configuration.

        Returns:
            AWS configuration dictionary
        """
        return self._config.get("aws", {})

    def get_home_region(self) -> str:
        """Get AWS home region.

        Returns:
            AWS home region string
        """
        return self.get("aws.home_region")

    def get_governed_regions(self) -> List[str]:
        """Get list of governed regions.

        Returns:
            List of AWS region strings
        """
        regions = self.get("aws.governed_regions", [])
        if not regions:
            regions = [self.get_home_region()]
        return regions

    def get_scp_tier(self) -> str:
        """Get SCP tier configuration.

        Returns:
            SCP tier string (basic, standard, or strict)
        """
        return self.get("scp_tier", "standard")

    def to_dict(self) -> Dict[str, Any]:
        """Get complete configuration as dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()
