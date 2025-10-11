"""Tests for Account Management functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.prerequisites.accounts import (
    AccountManager,
    AccountCreationError,
    InvalidEmailError,
    EmailInUseError
)
from src.core.aws_client import AWSClientManager


@pytest.fixture
def mock_aws_client():
    """Mock AWS client manager."""
    client = Mock(spec=AWSClientManager)
    client.get_current_region.return_value = 'us-east-1'
    return client


@pytest.fixture
def mock_org_client():
    """Mock Organizations client."""
    return Mock()


@pytest.fixture
def account_manager(mock_aws_client, mock_org_client):
    """Account manager with mocked client."""
    manager = AccountManager(mock_aws_client)
    mock_aws_client.get_client.return_value = mock_org_client
    return manager


class TestAccountManager:
    """Test AccountManager class."""

    def test_init(self, mock_aws_client):
        """Test AccountManager initialization."""
        manager = AccountManager(mock_aws_client)
        assert manager.aws_client == mock_aws_client
        assert manager._org_client is None

    def test_get_client(self, account_manager, mock_aws_client, mock_org_client):
        """Test client initialization and caching."""
        # First call should create client
        client = account_manager._get_client()
        assert client == mock_org_client
        mock_aws_client.get_client.assert_called_once_with(
            'organizations', 'us-east-1'
        )
        
        # Second call should use cached client
        client2 = account_manager._get_client()
        assert client2 == mock_org_client
        assert mock_aws_client.get_client.call_count == 1

    def test_validate_email_address_valid(self, account_manager):
        """Test email validation with valid email."""
        with patch.object(account_manager, 'check_email_availability', 
                         return_value=True):
            result = account_manager.validate_email_address('test@example.com')
            assert result is True

    def test_validate_email_address_invalid_format(self, account_manager):
        """Test email validation with invalid format."""
        with pytest.raises(InvalidEmailError, match="Invalid email format"):
            account_manager.validate_email_address('invalid-email')

    def test_validate_email_address_in_use(self, account_manager):
        """Test email validation when email is in use."""
        with patch.object(account_manager, 'check_email_availability', 
                         return_value=False):
            with pytest.raises(EmailInUseError, match="already in use"):
                account_manager.validate_email_address('test@example.com')

    def test_check_email_availability_available(self, account_manager, 
                                               mock_org_client):
        """Test email availability check when email is available."""
        mock_org_client.list_accounts.return_value = {
            'Accounts': [
                {'Email': 'other@example.com', 'Id': '123456789012'}
            ]
        }
        
        result = account_manager.check_email_availability('test@example.com')
        assert result is True

    def test_check_email_availability_in_use(self, account_manager, 
                                            mock_org_client):
        """Test email availability check when email is in use."""
        mock_org_client.list_accounts.return_value = {
            'Accounts': [
                {'Email': 'test@example.com', 'Id': '123456789012'}
            ]
        }
        
        result = account_manager.check_email_availability('test@example.com')
        assert result is False

    def test_check_email_availability_case_insensitive(self, account_manager, 
                                                      mock_org_client):
        """Test email availability check is case insensitive."""
        mock_org_client.list_accounts.return_value = {
            'Accounts': [
                {'Email': 'TEST@EXAMPLE.COM', 'Id': '123456789012'}
            ]
        }
        
        result = account_manager.check_email_availability('test@example.com')
        assert result is False

    def test_check_email_availability_client_error(self, account_manager, 
                                                   mock_org_client):
        """Test email availability check handles client errors."""
        mock_org_client.list_accounts.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'ListAccounts'
        )
        
        result = account_manager.check_email_availability('test@example.com')
        assert result is True

    @patch('src.prerequisites.accounts.time.sleep')
    def test_create_account_success(self, mock_sleep, account_manager, 
                                   mock_org_client):
        """Test successful account creation."""
        mock_org_client.create_account.return_value = {
            'CreateAccountStatus': {'Id': 'req-123'}
        }
        mock_org_client.describe_create_account_status.return_value = {
            'CreateAccountStatus': {
                'State': 'SUCCEEDED',
                'AccountId': '123456789012'
            }
        }
        
        with patch.object(account_manager, 'validate_email_address'):
            account_id, request_id = account_manager.create_account(
                'Test Account', 'test@example.com'
            )
            
        assert account_id == '123456789012'
        assert request_id == 'req-123'

    def test_create_account_invalid_email(self, account_manager):
        """Test account creation with invalid email."""
        with patch.object(account_manager, 'validate_email_address', 
                         side_effect=InvalidEmailError("Invalid email")):
            with pytest.raises(InvalidEmailError):
                account_manager.create_account('Test', 'invalid')

    def test_create_account_constraint_violation(self, account_manager, 
                                                mock_org_client):
        """Test account creation constraint violation."""
        mock_org_client.create_account.side_effect = ClientError(
            {'Error': {'Code': 'ConstraintViolationException'}}, 
            'CreateAccount'
        )
        
        with patch.object(account_manager, 'validate_email_address'):
            with pytest.raises(AccountCreationError, 
                             match="constraint violation"):
                account_manager.create_account('Test', 'test@example.com')

    @patch('src.prerequisites.accounts.time.sleep')
    @patch('src.prerequisites.accounts.time.time')
    def test_wait_for_account_creation_timeout(self, mock_time, mock_sleep, 
                                              account_manager, mock_org_client):
        """Test account creation timeout."""
        mock_time.side_effect = [0, 1000]  # Simulate timeout
        mock_org_client.describe_create_account_status.return_value = {
            'CreateAccountStatus': {'State': 'IN_PROGRESS'}
        }
        
        with pytest.raises(AccountCreationError, match="timed out"):
            account_manager._wait_for_account_creation('req-123', timeout=900)

    @patch('src.prerequisites.accounts.time.sleep')
    def test_wait_for_account_creation_failed(self, mock_sleep, 
                                             account_manager, mock_org_client):
        """Test account creation failure."""
        mock_org_client.describe_create_account_status.return_value = {
            'CreateAccountStatus': {
                'State': 'FAILED',
                'FailureReason': 'Email already in use'
            }
        }
        
        with pytest.raises(AccountCreationError, match="Email already in use"):
            account_manager._wait_for_account_creation('req-123')

    def test_get_account_status_success(self, account_manager, mock_org_client):
        """Test getting account status successfully."""
        expected_status = {
            'State': 'SUCCEEDED',
            'AccountId': '123456789012'
        }
        mock_org_client.describe_create_account_status.return_value = {
            'CreateAccountStatus': expected_status
        }
        
        status = account_manager.get_account_status('req-123')
        assert status == expected_status

    def test_get_account_status_not_found(self, account_manager, 
                                         mock_org_client):
        """Test getting account status when not found."""
        mock_org_client.describe_create_account_status.side_effect = ClientError(
            {'Error': {'Code': 'CreateAccountStatusNotFoundException'}}, 
            'DescribeCreateAccountStatus'
        )
        
        status = account_manager.get_account_status('req-123')
        assert status is None

    def test_move_account_to_ou_success(self, account_manager, mock_org_client):
        """Test moving account to OU successfully."""
        mock_org_client.list_roots.return_value = {
            'Roots': [{'Id': 'r-1234'}]
        }
        
        result = account_manager.move_account_to_ou('123456789012', 'ou-5678')
        assert result is True
        
        mock_org_client.move_account.assert_called_once_with(
            AccountId='123456789012',
            SourceParentId='r-1234',
            DestinationParentId='ou-5678'
        )

    def test_move_account_to_ou_failure(self, account_manager, mock_org_client):
        """Test moving account to OU failure."""
        mock_org_client.list_roots.return_value = {
            'Roots': [{'Id': 'r-1234'}]
        }
        mock_org_client.move_account.side_effect = ClientError(
            {'Error': {'Code': 'AccountNotFoundException'}}, 'MoveAccount'
        )
        
        with pytest.raises(AccountCreationError, match="Failed to move account"):
            account_manager.move_account_to_ou('123456789012', 'ou-5678')

    def test_get_root_id(self, account_manager, mock_org_client):
        """Test getting root ID."""
        mock_org_client.list_roots.return_value = {
            'Roots': [{'Id': 'r-1234'}]
        }
        
        root_id = account_manager._get_root_id()
        assert root_id == 'r-1234'

    def test_list_accounts_success(self, account_manager, mock_org_client):
        """Test listing accounts successfully."""
        expected_accounts = [
            {'Id': '123456789012', 'Email': 'test@example.com'}
        ]
        mock_org_client.list_accounts.return_value = {
            'Accounts': expected_accounts
        }
        
        accounts = account_manager.list_accounts()
        assert accounts == expected_accounts

    def test_list_accounts_failure(self, account_manager, mock_org_client):
        """Test listing accounts failure."""
        mock_org_client.list_accounts.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'ListAccounts'
        )
        
        with pytest.raises(AccountCreationError, match="Failed to list accounts"):
            account_manager.list_accounts()

    def test_find_account_by_email_found(self, account_manager):
        """Test finding account by email when found."""
        expected_account = {'Id': '123456789012', 'Email': 'test@example.com'}
        with patch.object(account_manager, 'list_accounts', 
                         return_value=[expected_account]):
            account = account_manager.find_account_by_email('test@example.com')
            assert account == expected_account

    def test_find_account_by_email_not_found(self, account_manager):
        """Test finding account by email when not found."""
        with patch.object(account_manager, 'list_accounts', return_value=[]):
            account = account_manager.find_account_by_email('test@example.com')
            assert account is None

    def test_find_account_by_email_case_insensitive(self, account_manager):
        """Test finding account by email is case insensitive."""
        expected_account = {'Id': '123456789012', 'Email': 'TEST@EXAMPLE.COM'}
        with patch.object(account_manager, 'list_accounts', 
                         return_value=[expected_account]):
            account = account_manager.find_account_by_email('test@example.com')
            assert account == expected_account

    def test_create_account_service_exception(self, account_manager, 
                                             mock_org_client):
        """Test account creation service exception."""
        mock_org_client.create_account.side_effect = ClientError(
            {'Error': {'Code': 'ServiceException'}}, 'CreateAccount'
        )
        
        with patch.object(account_manager, 'validate_email_address'):
            with pytest.raises(AccountCreationError, 
                             match="AWS service error"):
                account_manager.create_account('Test', 'test@example.com')

    def test_create_account_other_exception(self, account_manager, 
                                           mock_org_client):
        """Test account creation other exception."""
        mock_org_client.create_account.side_effect = ClientError(
            {'Error': {'Code': 'UnknownException'}}, 'CreateAccount'
        )
        
        with patch.object(account_manager, 'validate_email_address'):
            with pytest.raises(AccountCreationError, 
                             match="Account creation failed"):
                account_manager.create_account('Test', 'test@example.com')

    @patch('src.prerequisites.accounts.time.sleep')
    def test_wait_for_account_creation_client_error(self, mock_sleep, 
                                                   account_manager, 
                                                   mock_org_client):
        """Test account creation status check client error."""
        mock_org_client.describe_create_account_status.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'DescribeCreateAccountStatus'
        )
        
        with pytest.raises(AccountCreationError, 
                         match="Failed to check account creation status"):
            account_manager._wait_for_account_creation('req-123')
