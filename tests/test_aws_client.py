"""Unit tests for AWS Client Manager."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import NoCredentialsError, ProfileNotFound

from src.core.aws_client import AWSClientManager


class TestAWSClientManager:
    """Test cases for AWSClientManager class."""

    @patch("src.core.aws_client.boto3.Session")
    def test_init_success(self, mock_session_class):
        """Test successful initialization."""
        mock_session = Mock()
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012"
        }
        mock_session.client.return_value = mock_sts_client
        mock_session_class.return_value = mock_session

        manager = AWSClientManager()

        assert manager._profile_name is None
        mock_sts_client.get_caller_identity.assert_called_once()

    @patch("src.core.aws_client.boto3.Session")
    def test_init_with_profile(self, mock_session_class):
        """Test initialization with profile."""
        mock_session = Mock()
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012"
        }
        mock_session.client.return_value = mock_sts_client
        mock_session_class.return_value = mock_session

        manager = AWSClientManager(profile_name="test-profile")

        assert manager._profile_name == "test-profile"
        mock_session_class.assert_called_with(profile_name="test-profile")

    @patch("src.core.aws_client.boto3.Session")
    def test_init_no_credentials(self, mock_session_class):
        """Test initialization with no credentials."""
        mock_session = Mock()
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.side_effect = NoCredentialsError()
        mock_session.client.return_value = mock_sts_client
        mock_session_class.return_value = mock_session

        with pytest.raises(NoCredentialsError):
            AWSClientManager()

    @patch("src.core.aws_client.boto3.Session")
    def test_init_profile_not_found(self, mock_session_class):
        """Test initialization with invalid profile."""
        mock_session_class.side_effect = ProfileNotFound(profile="invalid")

        with pytest.raises(ProfileNotFound):
            AWSClientManager(profile_name="invalid")

    @patch("src.core.aws_client.boto3.Session")
    def test_get_client_caching(self, mock_session_class):
        """Test client caching functionality."""
        mock_session = Mock()
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012"
        }
        mock_ec2_client = Mock()

        def client_side_effect(service_name, region_name=None):
            if service_name == "sts":
                return mock_sts_client
            elif service_name == "ec2":
                return mock_ec2_client
            return Mock()

        mock_session.client.side_effect = client_side_effect
        mock_session_class.return_value = mock_session

        manager = AWSClientManager()

        # First call should create client
        client1 = manager.get_client("ec2", "us-east-1")
        # Second call should return cached client
        client2 = manager.get_client("ec2", "us-east-1")

        assert client1 is client2
        assert client1 is mock_ec2_client

    @patch("src.core.aws_client.boto3.Session")
    def test_get_current_region(self, mock_session_class):
        """Test getting current region."""
        mock_session = Mock()
        mock_session.region_name = "us-west-2"
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012"
        }
        mock_session.client.return_value = mock_sts_client
        mock_session_class.return_value = mock_session

        manager = AWSClientManager()
        region = manager.get_current_region()

        assert region == "us-west-2"

    @patch("src.core.aws_client.boto3.Session")
    def test_get_current_region_default(self, mock_session_class):
        """Test getting current region with default fallback."""
        mock_session = Mock()
        mock_session.region_name = None
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012"
        }
        mock_session.client.return_value = mock_sts_client
        mock_session_class.return_value = mock_session

        manager = AWSClientManager()
        region = manager.get_current_region()

        assert region == "us-east-1"

    @patch("src.core.aws_client.boto3.Session")
    def test_get_account_id(self, mock_session_class):
        """Test getting account ID."""
        mock_session = Mock()
        mock_session.region_name = "us-east-1"
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012"
        }
        mock_session.client.return_value = mock_sts_client
        mock_session_class.return_value = mock_session

        manager = AWSClientManager()
        account_id = manager.get_account_id()

        assert account_id == "123456789012"

    @patch("src.core.aws_client.boto3.Session")
    def test_clear_cache(self, mock_session_class):
        """Test clearing client cache."""
        mock_session = Mock()
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {
            "Account": "123456789012"
        }
        mock_ec2_client = Mock()

        def client_side_effect(service_name, region_name=None):
            if service_name == "sts":
                return mock_sts_client
            elif service_name == "ec2":
                return mock_ec2_client
            return Mock()

        mock_session.client.side_effect = client_side_effect
        mock_session_class.return_value = mock_session

        manager = AWSClientManager()

        # Create a client to populate cache
        manager.get_client("ec2", "us-east-1")
        assert len(manager._clients) == 1

        # Clear cache
        manager.clear_cache()
        assert len(manager._clients) == 0
