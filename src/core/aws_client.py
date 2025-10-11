"""Centralized AWS client management with session handling.

This module provides a centralized way to manage AWS clients across
different regions while maintaining session consistency and proper
error handling following AWS best practices.
"""

from typing import Dict, Optional
import boto3
from botocore.exceptions import (
    NoCredentialsError,
    ClientError,
    ProfileNotFound,
)


class AWSClientManager:
    """Centralized AWS client management with session handling.

    This class provides a centralized way to manage AWS clients across
    different regions while maintaining session consistency and proper
    error handling.
    """

    def __init__(self, profile_name: Optional[str] = None) -> None:
        """Initialize AWS client manager.

        Args:
            profile_name: Optional AWS profile name for credentials

        Raises:
            NoCredentialsError: When AWS credentials are not available
            ProfileNotFound: When specified profile doesn't exist
        """
        self._session: Optional[boto3.Session] = None
        self._clients: Dict[str, boto3.client] = {}
        self._profile_name = profile_name
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """Validate AWS credentials are available and working.

        Raises:
            NoCredentialsError: When AWS credentials are not available
            ProfileNotFound: When specified profile doesn't exist
        """
        try:
            session = self._get_session()
            # Test credentials by getting caller identity
            sts_client = session.client("sts")
            sts_client.get_caller_identity()
        except NoCredentialsError:
            raise NoCredentialsError()
        except ProfileNotFound:
            raise ProfileNotFound(profile=self._profile_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidUserID.NotFound":
                raise NoCredentialsError(
                    "AWS credentials are invalid or expired. "
                    "Please update your credentials."
                )
            raise

    def _get_session(self) -> boto3.Session:
        """Get or create boto3 session.

        Returns:
            Configured boto3 session
        """
        if self._session is None:
            if self._profile_name:
                self._session = boto3.Session(profile_name=self._profile_name)
            else:
                self._session = boto3.Session()
        return self._session

    def get_client(self, service_name: str, region_name: str) -> boto3.client:
        """Get AWS service client for specified region.

        Args:
            service_name: AWS service name (e.g., 'organizations', 'iam')
            region_name: AWS region name (e.g., 'us-east-1')

        Returns:
            Configured boto3 client for the service and region

        Raises:
            ClientError: When AWS API call fails
        """
        client_key = f"{service_name}_{region_name}"

        if client_key not in self._clients:
            session = self._get_session()
            self._clients[client_key] = session.client(
                service_name, region_name=region_name
            )

        return self._clients[client_key]

    def get_current_region(self) -> str:
        """Get current AWS region from session.

        Returns:
            Current AWS region name
        """
        session = self._get_session()
        return session.region_name or "us-east-1"

    def get_account_id(self) -> str:
        """Get current AWS account ID.

        Returns:
            Current AWS account ID

        Raises:
            ClientError: When unable to get account information
        """
        sts_client = self.get_client("sts", self.get_current_region())
        response = sts_client.get_caller_identity()
        return response["Account"]

    def clear_cache(self) -> None:
        """Clear cached clients to force recreation."""
        self._clients.clear()
