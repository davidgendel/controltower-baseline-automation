"""Tests for Account Structure Validator."""

import pytest
from unittest.mock import Mock, patch

from src.prerequisites.validators.account_validator import AccountStructureValidator
from src.core.aws_client import AWSClientManager
from src.core.validator import ValidationStatus


@pytest.fixture
def mock_aws_client():
    """Mock AWS client manager."""
    return Mock(spec=AWSClientManager)


@pytest.fixture
def mock_account_manager():
    """Mock account manager."""
    return Mock()


@pytest.fixture
def validator(mock_aws_client, mock_account_manager):
    """Account structure validator with mocked dependencies."""
    validator = AccountStructureValidator(mock_aws_client)
    validator.account_manager = mock_account_manager
    return validator


class TestAccountStructureValidator:
    """Test AccountStructureValidator class."""

    def test_init(self, mock_aws_client):
        """Test validator initialization."""
        validator = AccountStructureValidator(mock_aws_client)
        assert validator.aws_client == mock_aws_client
        assert validator.account_manager is not None

    def test_validate_success(self, validator, mock_account_manager):
        """Test successful validation with all required accounts."""
        mock_account_manager.list_accounts.return_value = [
            {'Id': '111111111111', 'Name': 'Log Archive', 'Email': 'log@example.com'},
            {'Id': '222222222222', 'Name': 'Audit', 'Email': 'audit@example.com'}
        ]
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.PASSED
        assert "successfully" in result.message
        assert "log_archive_account" in result.details
        assert "audit_account" in result.details

    def test_validate_missing_log_archive(self, validator, mock_account_manager):
        """Test validation with missing Log Archive account."""
        mock_account_manager.list_accounts.return_value = [
            {'Id': '222222222222', 'Name': 'Audit', 'Email': 'audit@example.com'}
        ]
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.FAILED
        assert "Required accounts missing" in result.message
        assert "Log Archive account not found" in result.details["missing_accounts"]
        assert any("Log Archive" in step for step in result.remediation_steps)

    def test_validate_missing_audit(self, validator, mock_account_manager):
        """Test validation with missing Audit account."""
        mock_account_manager.list_accounts.return_value = [
            {'Id': '111111111111', 'Name': 'Log Archive', 'Email': 'log@example.com'}
        ]
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.FAILED
        assert "Required accounts missing" in result.message
        assert "Audit account not found" in result.details["missing_accounts"]
        assert any("Audit" in step for step in result.remediation_steps)

    def test_validate_missing_both_accounts(self, validator, mock_account_manager):
        """Test validation with both accounts missing."""
        mock_account_manager.list_accounts.return_value = [
            {'Id': '333333333333', 'Name': 'Production', 'Email': 'prod@example.com'}
        ]
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.FAILED
        assert len(result.details["missing_accounts"]) == 2
        assert "Log Archive account not found" in result.details["missing_accounts"]
        assert "Audit account not found" in result.details["missing_accounts"]

    def test_validate_exception(self, validator, mock_account_manager):
        """Test validation with exception."""
        mock_account_manager.list_accounts.side_effect = Exception("API Error")
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.FAILED
        assert "Account validation failed" in result.message
        assert "API Error" in result.details["error"]

    def test_check_log_archive_account_found(self, validator, mock_account_manager):
        """Test finding Log Archive account."""
        expected_account = {'Id': '111111111111', 'Name': 'Log Archive'}
        mock_account_manager.list_accounts.return_value = [expected_account]
        
        result = validator._check_log_archive_account()
        
        assert result == expected_account

    def test_check_log_archive_account_not_found(self, validator, mock_account_manager):
        """Test Log Archive account not found."""
        mock_account_manager.list_accounts.return_value = [
            {'Id': '222222222222', 'Name': 'Production'}
        ]
        
        result = validator._check_log_archive_account()
        
        assert result is None

    def test_check_audit_account_found(self, validator, mock_account_manager):
        """Test finding Audit account."""
        expected_account = {'Id': '222222222222', 'Name': 'Audit'}
        mock_account_manager.list_accounts.return_value = [expected_account]
        
        result = validator._check_audit_account()
        
        assert result == expected_account

    def test_check_audit_account_not_found(self, validator, mock_account_manager):
        """Test Audit account not found."""
        mock_account_manager.list_accounts.return_value = [
            {'Id': '111111111111', 'Name': 'Production'}
        ]
        
        result = validator._check_audit_account()
        
        assert result is None

    def test_get_remediation_steps_log_archive(self, validator):
        """Test remediation steps for missing Log Archive account."""
        issues = ["Log Archive account not found"]
        
        steps = validator._get_remediation_steps(issues)
        
        assert any("Log Archive" in step for step in steps)
        assert any("create_account" in step for step in steps)

    def test_get_remediation_steps_audit(self, validator):
        """Test remediation steps for missing Audit account."""
        issues = ["Audit account not found"]
        
        steps = validator._get_remediation_steps(issues)
        
        assert any("Audit" in step for step in steps)
        assert any("create_account" in step for step in steps)

    def test_get_remediation_steps_both(self, validator):
        """Test remediation steps for both missing accounts."""
        issues = ["Log Archive account not found", "Audit account not found"]
        
        steps = validator._get_remediation_steps(issues)
        
        assert any("Log Archive" in step for step in steps)
        assert any("Audit" in step for step in steps)
