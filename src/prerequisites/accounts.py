"""Account creation and management for Control Tower prerequisites.

This module handles creating Log Archive and Audit accounts, validating
account status, and moving accounts to appropriate organizational units.
"""

import re
import time
from typing import Dict, List, Optional, Tuple, Any
from botocore.exceptions import ClientError

from src.core.aws_client import AWSClientManager


class AccountCreationError(Exception):
    """Base exception for account creation operations."""
    pass


class InvalidEmailError(AccountCreationError):
    """Raised when email address is invalid."""
    pass


class EmailInUseError(AccountCreationError):
    """Raised when email address is already in use."""
    pass


class AccountManager:
    """Manages AWS account creation and management for Control Tower.
    
    This class handles creating Log Archive and Audit accounts,
    validating account status, and managing account placement in OUs.
    """
    
    def __init__(self, aws_client: AWSClientManager) -> None:
        """Initialize Account manager.
        
        Args:
            aws_client: Configured AWS client manager
        """
        self.aws_client = aws_client
        self._org_client = None
        
    def _get_client(self):
        """Get Organizations client with caching.
        
        Returns:
            Configured Organizations client
        """
        if self._org_client is None:
            self._org_client = self.aws_client.get_client(
                'organizations',
                self.aws_client.get_current_region()
            )
        return self._org_client
        
    def validate_email_address(self, email: str) -> bool:
        """Validate email address format and uniqueness.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email is valid and available
            
        Raises:
            InvalidEmailError: When email format is invalid
            EmailInUseError: When email is already used
        """
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise InvalidEmailError(f"Invalid email format: {email}")
            
        # Check if email is already in use
        if not self.check_email_availability(email):
            raise EmailInUseError(f"Email address already in use: {email}")
            
        return True
        
    def check_email_availability(self, email: str) -> bool:
        """Check if email address is available for account creation.
        
        Args:
            email: Email address to check
            
        Returns:
            True if email is available, False if in use
        """
        try:
            client = self._get_client()
            response = client.list_accounts()
            
            for account in response['Accounts']:
                if account['Email'].lower() == email.lower():
                    return False
                    
            return True
            
        except ClientError:
            # If we can't check, assume available
            return True
            
    def create_account(self, name: str, email: str) -> Tuple[str, str]:
        """Create a new AWS account in the organization.
        
        Args:
            name: Account name
            email: Account email address
            
        Returns:
            Tuple of (account_id, request_id)
            
        Raises:
            AccountCreationError: When account creation fails
        """
        try:
            # Validate email first
            self.validate_email_address(email)
            
            client = self._get_client()
            response = client.create_account(
                AccountName=name,
                Email=email
            )
            
            request_id = response['CreateAccountStatus']['Id']
            
            # Wait for account creation to complete
            account_id = self._wait_for_account_creation(request_id)
            
            return account_id, request_id
            
        except (InvalidEmailError, EmailInUseError):
            raise
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConstraintViolationException':
                raise AccountCreationError(
                    f"Account creation constraint violation: {e}"
                )
            elif error_code == 'ServiceException':
                raise AccountCreationError(
                    f"AWS service error during account creation: {e}"
                )
            else:
                raise AccountCreationError(f"Account creation failed: {e}")
                
    def _wait_for_account_creation(self, request_id: str, 
                                  timeout: int = 900) -> str:
        """Wait for account creation to complete.
        
        Args:
            request_id: Account creation request ID
            timeout: Maximum wait time in seconds (default 15 minutes)
            
        Returns:
            Account ID when creation succeeds
            
        Raises:
            AccountCreationError: When creation fails or times out
        """
        client = self._get_client()
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = client.describe_create_account_status(
                    CreateAccountRequestId=request_id
                )
                status = response['CreateAccountStatus']
                
                if status['State'] == 'SUCCEEDED':
                    return status['AccountId']
                elif status['State'] == 'FAILED':
                    failure_reason = status.get('FailureReason', 'Unknown')
                    raise AccountCreationError(
                        f"Account creation failed: {failure_reason}"
                    )
                    
                # Still in progress, wait and retry
                time.sleep(30)
                
            except ClientError as e:
                raise AccountCreationError(
                    f"Failed to check account creation status: {e}"
                )
                
        raise AccountCreationError(
            f"Account creation timed out after {timeout} seconds"
        )
        
    def get_account_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get account creation status.
        
        Args:
            request_id: Account creation request ID
            
        Returns:
            Account status dictionary or None if not found
        """
        try:
            client = self._get_client()
            response = client.describe_create_account_status(
                CreateAccountRequestId=request_id
            )
            return response['CreateAccountStatus']
        except ClientError:
            return None
            
    def move_account_to_ou(self, account_id: str, ou_id: str) -> bool:
        """Move account to organizational unit.
        
        Args:
            account_id: Account ID to move
            ou_id: Target organizational unit ID
            
        Returns:
            True if successful
            
        Raises:
            AccountCreationError: When move operation fails
        """
        try:
            client = self._get_client()
            
            # Get current parent (root)
            root_id = self._get_root_id()
            
            client.move_account(
                AccountId=account_id,
                SourceParentId=root_id,
                DestinationParentId=ou_id
            )
            
            return True
            
        except ClientError as e:
            raise AccountCreationError(f"Failed to move account: {e}")
            
    def _get_root_id(self) -> str:
        """Get organization root ID.
        
        Returns:
            Root ID string
        """
        client = self._get_client()
        response = client.list_roots()
        return response['Roots'][0]['Id']
        
    def list_accounts(self) -> List[Dict[str, Any]]:
        """List all accounts in the organization.
        
        Returns:
            List of account details
        """
        try:
            client = self._get_client()
            response = client.list_accounts()
            return response['Accounts']
        except ClientError as e:
            raise AccountCreationError(f"Failed to list accounts: {e}")
            
    def find_account_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find account by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            Account details if found, None otherwise
        """
        accounts = self.list_accounts()
        for account in accounts:
            if account['Email'].lower() == email.lower():
                return account
        return None
