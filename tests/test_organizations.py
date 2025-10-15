"""Unit tests for Organizations Manager."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.prerequisites.organizations import (
    OrganizationsManager,
    OrganizationsError,
    DuplicateOUError
)
from src.core.aws_client import AWSClientManager


class TestOrganizationsManager:
    """Test cases for OrganizationsManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_aws_client = Mock(spec=AWSClientManager)
        self.mock_org_client = Mock()
        self.mock_aws_client.get_client.return_value = self.mock_org_client
        self.mock_aws_client.get_current_region.return_value = 'us-east-1'
        
        self.manager = OrganizationsManager(self.mock_aws_client)
        
    def test_enable_all_features_already_enabled(self):
        """Test enable_all_features when already enabled."""
        self.mock_org_client.describe_organization.return_value = {
            'Organization': {'FeatureSet': 'ALL'}
        }
        
        result = self.manager.enable_all_features()
        
        assert result is True
        self.mock_org_client.enable_all_features.assert_not_called()
        
    def test_enable_all_features_success(self):
        """Test successful enable_all_features."""
        self.mock_org_client.describe_organization.return_value = {
            'Organization': {'FeatureSet': 'CONSOLIDATED_BILLING'}
        }
        
        result = self.manager.enable_all_features()
        
        assert result is True
        self.mock_org_client.enable_all_features.assert_called_once()
        
    def test_enable_all_features_concurrent_modification(self):
        """Test enable_all_features with concurrent modification."""
        self.mock_org_client.describe_organization.return_value = {
            'Organization': {'FeatureSet': 'CONSOLIDATED_BILLING'}
        }
        self.mock_org_client.enable_all_features.side_effect = ClientError(
            {'Error': {'Code': 'ConcurrentModificationException'}}, 
            'EnableAllFeatures'
        )
        
        with pytest.raises(OrganizationsError) as exc_info:
            self.manager.enable_all_features()
            
        assert "being modified" in str(exc_info.value)
        
    def test_get_organization_info_success(self):
        """Test successful get_organization_info."""
        expected_org = {
            'Id': 'o-example123456',
            'FeatureSet': 'ALL',
            'MasterAccountId': '123456789012'
        }
        self.mock_org_client.describe_organization.return_value = {
            'Organization': expected_org
        }
        
        result = self.manager.get_organization_info()
        
        assert result == expected_org
        
    def test_get_organization_info_error(self):
        """Test get_organization_info with error."""
        self.mock_org_client.describe_organization.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'DescribeOrganization'
        )
        
        with pytest.raises(OrganizationsError):
            self.manager.get_organization_info()
            
    def test_list_organizational_units_success(self):
        """Test successful list_organizational_units."""
        expected_ous = [
            {'Id': 'ou-root-123456789', 'Name': 'Security'},
            {'Id': 'ou-root-987654321', 'Name': 'Sandbox'}
        ]
        self.mock_org_client.list_organizational_units_for_parent.return_value = {
            'OrganizationalUnits': expected_ous
        }
        
        result = self.manager.list_organizational_units('r-1234')
        
        assert result == expected_ous
        self.mock_org_client.list_organizational_units_for_parent.assert_called_once_with(
            ParentId='r-1234'
        )
        
    def test_create_organizational_unit_success(self):
        """Test successful create_organizational_unit."""
        # Mock existing OUs (empty list)
        self.mock_org_client.list_organizational_units_for_parent.return_value = {
            'OrganizationalUnits': []
        }
        
        expected_ou = {
            'Id': 'ou-root-123456789',
            'Name': 'Security',
            'Arn': 'arn:aws:organizations::123456789012:ou/o-example123456/ou-root-123456789'
        }
        self.mock_org_client.create_organizational_unit.return_value = {
            'OrganizationalUnit': expected_ou
        }
        
        result = self.manager.create_organizational_unit('Security', 'r-1234')
        
        assert result == expected_ou
        self.mock_org_client.create_organizational_unit.assert_called_once_with(
            ParentId='r-1234',
            Name='Security'
        )
        
    def test_create_organizational_unit_duplicate(self):
        """Test create_organizational_unit with duplicate OU."""
        # Mock existing OU with same name
        existing_ous = [{'Id': 'ou-root-123456789', 'Name': 'Security'}]
        self.mock_org_client.list_organizational_units_for_parent.return_value = {
            'OrganizationalUnits': existing_ous
        }
        
        with pytest.raises(DuplicateOUError) as exc_info:
            self.manager.create_organizational_unit('Security', 'r-1234')
            
        assert "already exists" in str(exc_info.value)
        self.mock_org_client.create_organizational_unit.assert_not_called()
        
    def test_create_organizational_unit_api_duplicate_error(self):
        """Test create_organizational_unit with API duplicate error."""
        self.mock_org_client.list_organizational_units_for_parent.return_value = {
            'OrganizationalUnits': []
        }
        self.mock_org_client.create_organizational_unit.side_effect = ClientError(
            {'Error': {'Code': 'DuplicateOrganizationalUnitException'}},
            'CreateOrganizationalUnit'
        )
        
        with pytest.raises(DuplicateOUError):
            self.manager.create_organizational_unit('Security', 'r-1234')
            
    def test_get_root_id_success(self):
        """Test successful get_root_id."""
        expected_roots = [{'Id': 'r-1234', 'Name': 'Root'}]
        self.mock_org_client.list_roots.return_value = {
            'Roots': expected_roots
        }
        
        result = self.manager.get_root_id()
        
        assert result == 'r-1234'
        
    def test_get_root_id_no_roots(self):
        """Test get_root_id with no roots."""
        self.mock_org_client.list_roots.return_value = {'Roots': []}
        
        with pytest.raises(OrganizationsError) as exc_info:
            self.manager.get_root_id()
            
        assert "No roots found" in str(exc_info.value)
        
    def test_validate_organization_structure_valid(self):
        """Test validate_organization_structure with valid structure."""
        # Mock organization info
        org_info = {
            'Id': 'o-example123456',
            'FeatureSet': 'ALL',
            'MasterAccountId': '123456789012'
        }
        self.mock_org_client.describe_organization.return_value = {
            'Organization': org_info
        }
        
        # Mock root ID
        self.mock_org_client.list_roots.return_value = {
            'Roots': [{'Id': 'r-1234', 'Name': 'Root'}]
        }
        
        # Mock OUs
        ous = [
            {'Id': 'ou-root-123456789', 'Name': 'Security'},
            {'Id': 'ou-root-987654321', 'Name': 'Sandbox'}
        ]
        self.mock_org_client.list_organizational_units_for_parent.return_value = {
            'OrganizationalUnits': ous
        }
        
        result = self.manager.validate_organization_structure()
        
        assert result['valid'] is True
        assert len(result['issues']) == 0
        assert result['organization_info'] == org_info
        assert result['root_id'] == 'r-1234'
        assert result['security_ou']['Name'] == 'Security'
        assert result['sandbox_ou']['Name'] == 'Sandbox'
        
    def test_validate_organization_structure_invalid_features(self):
        """Test validate_organization_structure with invalid features."""
        org_info = {
            'Id': 'o-example123456',
            'FeatureSet': 'CONSOLIDATED_BILLING',
            'MasterAccountId': '123456789012'
        }
        self.mock_org_client.describe_organization.return_value = {
            'Organization': org_info
        }
        
        self.mock_org_client.list_roots.return_value = {
            'Roots': [{'Id': 'r-1234', 'Name': 'Root'}]
        }
        
        self.mock_org_client.list_organizational_units_for_parent.return_value = {
            'OrganizationalUnits': []
        }
        
        result = self.manager.validate_organization_structure()
        
        assert result['valid'] is False
        assert "all features enabled" in result['issues'][0]
        assert "Security OU not found" in result['issues']
        assert "Sandbox OU not found" in result['issues']
    
    def test_create_organization_success(self):
        """Test successful organization creation."""
        expected_org = {
            'Id': 'o-example123456',
            'MasterAccountId': '123456789012',
            'FeatureSet': 'ALL'
        }
        self.mock_org_client.create_organization.return_value = {
            'Organization': expected_org
        }
        
        result = self.manager.create_organization()
        
        assert result == expected_org
        self.mock_org_client.create_organization.assert_called_once_with(FeatureSet='ALL')
    
    def test_create_organization_already_exists(self):
        """Test create_organization when organization already exists."""
        # Mock create_organization to raise AlreadyInOrganizationException
        self.mock_org_client.create_organization.side_effect = ClientError(
            error_response={'Error': {'Code': 'AlreadyInOrganizationException'}},
            operation_name='CreateOrganization'
        )
        
        # Mock get_organization_info to return existing org
        expected_org = {
            'Id': 'o-existing123456',
            'MasterAccountId': '123456789012',
            'FeatureSet': 'ALL'
        }
        self.mock_org_client.describe_organization.return_value = {
            'Organization': expected_org
        }
        
        result = self.manager.create_organization()
        
        assert result == expected_org
    
    def test_create_organization_access_denied(self):
        """Test create_organization with access denied for dependency."""
        self.mock_org_client.create_organization.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDeniedForDependencyException'}},
            operation_name='CreateOrganization'
        )
        
        with pytest.raises(OrganizationsError) as exc_info:
            self.manager.create_organization()
        
        assert "iam:CreateServiceLinkedRole" in str(exc_info.value)
    
    def test_organization_exists_true(self):
        """Test organization_exists when organization exists."""
        self.mock_org_client.describe_organization.return_value = {
            'Organization': {'Id': 'o-example123456'}
        }
        
        result = self.manager.organization_exists()
        
        assert result is True
    
    def test_organization_exists_false(self):
        """Test organization_exists when organization doesn't exist."""
        self.mock_org_client.describe_organization.side_effect = ClientError(
            error_response={'Error': {'Code': 'AWSOrganizationsNotInUseException'}},
            operation_name='DescribeOrganization'
        )
        
        result = self.manager.organization_exists()
        
        assert result is False
