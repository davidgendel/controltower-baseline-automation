"""Unit tests for Configuration Management."""

import os
import tempfile
import pytest
import yaml

from src.core.config import Configuration, ConfigurationError


class TestConfiguration:
    """Test cases for Configuration class."""

    def test_load_valid_config(self):
        """Test loading valid configuration."""
        config_data = {
            "aws": {
                "home_region": "us-east-1",
                "governed_regions": ["us-east-1", "us-west-2"],
            },
            "scp_tier": "standard",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Configuration(config_path)
            assert config.get_home_region() == "us-east-1"
            assert config.get_governed_regions() == ["us-east-1", "us-west-2"]
            assert config.get_scp_tier() == "standard"
        finally:
            os.unlink(config_path)

    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        with pytest.raises(ConfigurationError) as exc_info:
            Configuration("/nonexistent/config.yaml")

        assert "Configuration file not found" in str(exc_info.value)

    def test_invalid_yaml(self):
        """Test handling of invalid YAML."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Configuration(config_path)

            assert "Invalid YAML" in str(exc_info.value)
        finally:
            os.unlink(config_path)

    def test_missing_required_section(self):
        """Test validation of missing required sections."""
        config_data = {"other": "value"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Configuration(config_path)

            assert "Required configuration section 'aws' is missing" in str(
                exc_info.value
            )
        finally:
            os.unlink(config_path)

    def test_missing_home_region(self):
        """Test validation of missing home region."""
        config_data = {"aws": {}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Configuration(config_path)

            assert "Required field 'aws.home_region' is missing" in str(
                exc_info.value
            )
        finally:
            os.unlink(config_path)

    def test_invalid_home_region(self):
        """Test validation of invalid home region."""
        config_data = {"aws": {"home_region": ""}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Configuration(config_path)

            assert "must be a non-empty string" in str(exc_info.value)
        finally:
            os.unlink(config_path)

    def test_environment_override_region(self):
        """Test environment variable override for region."""
        config_data = {"aws": {"home_region": "us-east-1"}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            # Set environment variable
            os.environ["AWS_REGION"] = "eu-west-1"

            config = Configuration(config_path)
            assert config.get_home_region() == "eu-west-1"

        finally:
            os.unlink(config_path)
            if "AWS_REGION" in os.environ:
                del os.environ["AWS_REGION"]

    def test_environment_override_profile(self):
        """Test environment variable override for profile."""
        config_data = {"aws": {"home_region": "us-east-1"}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            # Set environment variable
            os.environ["AWS_PROFILE"] = "test-profile"

            config = Configuration(config_path)
            assert config.get("aws.profile_name") == "test-profile"

        finally:
            os.unlink(config_path)
            if "AWS_PROFILE" in os.environ:
                del os.environ["AWS_PROFILE"]

    def test_home_region_added_to_governed_regions(self):
        """Test that home region is automatically added to governed regions."""
        config_data = {
            "aws": {
                "home_region": "us-east-1",
                "governed_regions": ["us-west-2", "eu-west-1"],
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Configuration(config_path)
            governed_regions = config.get_governed_regions()
            assert "us-east-1" in governed_regions
            assert governed_regions[0] == "us-east-1"  # Should be first
        finally:
            os.unlink(config_path)

    def test_get_nested_value(self):
        """Test getting nested configuration values."""
        config_data = {
            "aws": {
                "home_region": "us-east-1",
                "nested": {"deep": {"value": "test"}},
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Configuration(config_path)
            assert config.get("aws.nested.deep.value") == "test"
            assert config.get("aws.nonexistent", "default") == "default"
        finally:
            os.unlink(config_path)

    def test_default_scp_tier(self):
        """Test default SCP tier value."""
        config_data = {"aws": {"home_region": "us-east-1"}}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Configuration(config_path)
            assert config.get_scp_tier() == "standard"
        finally:
            os.unlink(config_path)

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config_data = {
            "aws": {"home_region": "us-east-1"},
            "scp_tier": "basic",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Configuration(config_path)
            config_dict = config.to_dict()
            assert config_dict["aws"]["home_region"] == "us-east-1"
            assert config_dict["scp_tier"] == "basic"
        finally:
            os.unlink(config_path)
