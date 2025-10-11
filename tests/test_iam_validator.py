"""Tests for IAM roles validator."""

import pytest
from unittest.mock import Mock

from src.prerequisites.validators.iam_validator import IAMRolesValidator
from src.core.aws_client import AWSClientManager
from src.core.validator import ValidationStatus


@pytest.fixture
def mock_aws_client():
    """Mock AWS client manager."""
    return Mock(spec=AWSClientManager)


@pytest.fixture
def mock_iam_manager():
    """Mock IAM manager."""
    return Mock()


@pytest.fixture
def validator(mock_aws_client, mock_iam_manager):
    """IAM roles validator with mocked dependencies."""
    validator = IAMRolesValidator(mock_aws_client)
    validator.iam_manager = mock_iam_manager
    return validator


class TestIAMRolesValidator:
    """Test IAMRolesValidator class."""

    def test_init(self, mock_aws_client):
        """Test validator initialization."""
        validator = IAMRolesValidator(mock_aws_client)
        assert validator.aws_client == mock_aws_client
        assert validator.name == "IAM Roles"

    def test_validate_all_roles_exist(self, validator, mock_iam_manager):
        """Test validation when all roles exist with valid trust policies."""
        mock_iam_manager.get_roles_summary.return_value = {
            'total_roles': 3,
            'existing_roles': 3,
            'missing_roles': [],
            'role_details': {
                'AWSControlTowerAdmin': {'exists': True, 'trust_policy_valid': True},
                'AWSControlTowerStackSetRole': {'exists': True, 'trust_policy_valid': True},
                'AWSControlTowerCloudTrailRole': {'exists': True, 'trust_policy_valid': True}
            }
        }
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.PASSED
        assert "successfully" in result.message

    def test_validate_missing_roles(self, validator, mock_iam_manager):
        """Test validation with missing roles."""
        mock_iam_manager.get_roles_summary.return_value = {
            'total_roles': 3,
            'existing_roles': 1,
            'missing_roles': ['AWSControlTowerStackSetRole', 'AWSControlTowerCloudTrailRole'],
            'role_details': {
                'AWSControlTowerAdmin': {'exists': True, 'trust_policy_valid': True},
                'AWSControlTowerStackSetRole': {'exists': False, 'trust_policy_valid': False},
                'AWSControlTowerCloudTrailRole': {'exists': False, 'trust_policy_valid': False}
            }
        }
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.WARNING
        assert "created automatically" in result.message
        assert len(result.details["missing_roles"]) == 2
        assert any("Control Tower will create" in step for step in result.remediation_steps)

    def test_validate_trust_policy_issues(self, validator, mock_iam_manager):
        """Test validation with trust policy issues."""
        mock_iam_manager.get_roles_summary.return_value = {
            'total_roles': 3,
            'existing_roles': 3,
            'missing_roles': [],
            'role_details': {
                'AWSControlTowerAdmin': {'exists': True, 'trust_policy_valid': False},
                'AWSControlTowerStackSetRole': {'exists': True, 'trust_policy_valid': True},
                'AWSControlTowerCloudTrailRole': {'exists': True, 'trust_policy_valid': True}
            }
        }
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.WARNING
        assert "invalid trust policies" in result.message
        assert "AWSControlTowerAdmin" in result.details["roles_with_trust_issues"]
        assert any("trust policies" in step for step in result.remediation_steps)

    def test_validate_exception(self, validator, mock_iam_manager):
        """Test validation with exception."""
        mock_iam_manager.get_roles_summary.side_effect = Exception("IAM API Error")
        
        result = validator.validate()
        
        assert result.status == ValidationStatus.FAILED
        assert "validation failed" in result.message
        assert "IAM API Error" in result.details["error"]

    def test_get_remediation_steps(self, validator):
        """Test remediation steps generation."""
        missing_roles = ['AWSControlTowerAdmin', 'AWSControlTowerStackSetRole']
        
        steps = validator._get_remediation_steps(missing_roles)
        
        assert any("Control Tower will create" in step for step in steps)
        assert any("AWSControlTowerAdmin" in step for step in steps)
        assert any("AWSControlTowerStackSetRole" in step for step in steps)
        assert any("No manual action required" in step for step in steps)
