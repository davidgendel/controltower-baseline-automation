"""Tests for Control Tower manifest generation functionality."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.control_tower.manifest import ManifestGenerator, ManifestValidationError
from src.core.aws_client import AWSClientManager
from src.core.config import Configuration


class TestManifestGenerator:
    """Test cases for ManifestGenerator class."""
    
    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create mock AWS client manager."""
        manager = Mock(spec=AWSClientManager)
        mock_client = Mock()
        manager.get_client.return_value = mock_client
        return manager
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        
        # AWS configuration
        config.aws = Mock()
        config.aws.governed_regions = ['us-east-1', 'us-west-2']
        
        # Organization configuration
        config.organization = Mock()
        config.organization.security_ou_name = 'Security'
        config.organization.additional_ous = [
            {'name': 'Sandbox', 'parent': 'Root'}
        ]
        
        # Accounts configuration
        config.accounts = Mock()
        config.accounts.log_archive = Mock()
        config.accounts.log_archive.name = 'Log Archive'
        config.accounts.audit = Mock()
        config.accounts.audit.name = 'Audit'
        
        # Identity Center configuration
        config.identity_center = Mock()
        config.identity_center.enabled = True
        
        # Logging configuration
        config.logging = Mock()
        config.logging.cloudtrail_enabled = True
        
        return config
    
    @pytest.fixture
    def generator(self, mock_config, mock_aws_client_manager):
        """Create ManifestGenerator instance."""
        return ManifestGenerator(mock_config, mock_aws_client_manager)
    
    @pytest.fixture
    def mock_accounts_response(self):
        """Create mock accounts list response."""
        return {
            'Accounts': [
                {
                    'Id': '111111111111',
                    'Name': 'Log Archive',
                    'Status': 'ACTIVE'
                },
                {
                    'Id': '222222222222',
                    'Name': 'Audit',
                    'Status': 'ACTIVE'
                },
                {
                    'Id': '333333333333',
                    'Name': 'Production',
                    'Status': 'ACTIVE'
                }
            ]
        }
    
    def test_init(self, mock_config, mock_aws_client_manager):
        """Test generator initialization."""
        generator = ManifestGenerator(mock_config, mock_aws_client_manager)
        
        assert generator.config == mock_config
        assert generator.aws_client_manager == mock_aws_client_manager
        assert generator._organizations_client is None
    
    def test_organizations_client_property(self, generator, mock_aws_client_manager):
        """Test lazy initialization of Organizations client."""
        # First access should create client
        client = generator.organizations_client
        mock_aws_client_manager.get_client.assert_called_once_with('organizations')
        
        # Second access should return same client
        client2 = generator.organizations_client
        assert client == client2
        assert mock_aws_client_manager.get_client.call_count == 1
    
    def test_generate_manifest_success(self, generator, mock_accounts_response):
        """Test successful manifest generation."""
        # Ensure no optional attributes exist for basic test
        if hasattr(generator.config.logging, 'retention_days'):
            delattr(generator.config.logging, 'retention_days')
        if hasattr(generator.config.logging, 'kms_key_arn'):
            delattr(generator.config.logging, 'kms_key_arn')
        
        # Mock the paginator for list_accounts
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [mock_accounts_response]
        generator.organizations_client.get_paginator.return_value = mock_paginator
        
        manifest = generator.generate_manifest()
        
        expected_manifest = {
            'governedRegions': ['us-east-1', 'us-west-2'],
            'organizationStructure': {
                'security': {'name': 'Security'},
                'sandbox': {'name': 'Sandbox'}
            },
            'centralizedLogging': {
                'accountId': '111111111111',
                'enabled': True
            },
            'securityRoles': {
                'accountId': '222222222222'
            },
            'accessManagement': {
                'enabled': True
            }
        }
        
        assert manifest == expected_manifest
    
    def test_generate_manifest_without_identity_center(self, generator, mock_accounts_response):
        """Test manifest generation without Identity Center."""
        generator.config.identity_center.enabled = False
        
        # Mock the paginator for list_accounts
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [mock_accounts_response]
        generator.organizations_client.get_paginator.return_value = mock_paginator
        
        manifest = generator.generate_manifest()
        
        # Should not include accessManagement
        assert 'accessManagement' not in manifest
        assert 'governedRegions' in manifest
        assert 'organizationStructure' in manifest
        assert 'centralizedLogging' in manifest
        assert 'securityRoles' in manifest
    
    def test_generate_manifest_account_resolution_failure(self, generator):
        """Test manifest generation with account resolution failure."""
        # Mock empty accounts response
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{'Accounts': []}]
        generator.organizations_client.get_paginator.return_value = mock_paginator
        
        with pytest.raises(ManifestValidationError, match="Failed to generate manifest"):
            generator.generate_manifest()
    
    def test_resolve_account_ids_success(self, generator, mock_accounts_response):
        """Test successful account ID resolution."""
        # Mock the paginator for list_accounts
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [mock_accounts_response]
        generator.organizations_client.get_paginator.return_value = mock_paginator
        
        account_names = ['Log Archive', 'Audit']
        account_mapping = generator.resolve_account_ids(account_names)
        
        expected_mapping = {
            'Log Archive': '111111111111',
            'Audit': '222222222222'
        }
        
        assert account_mapping == expected_mapping
    
    def test_resolve_account_ids_missing_account(self, generator, mock_accounts_response):
        """Test account ID resolution with missing account."""
        # Mock the paginator for list_accounts
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [mock_accounts_response]
        generator.organizations_client.get_paginator.return_value = mock_paginator
        
        account_names = ['Log Archive', 'Audit', 'NonExistent']
        
        with pytest.raises(ManifestValidationError, match="Could not find accounts: NonExistent"):
            generator.resolve_account_ids(account_names)
    
    def test_resolve_account_ids_api_error(self, generator):
        """Test account ID resolution with API error."""
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Insufficient permissions'
            }
        }
        generator.organizations_client.get_paginator.side_effect = ClientError(
            error_response, 'ListAccounts'
        )
        
        with pytest.raises(ManifestValidationError, match="Failed to resolve account IDs"):
            generator.resolve_account_ids(['Log Archive'])
    
    def test_validate_manifest_success(self, generator):
        """Test successful manifest validation."""
        valid_manifest = {
            'governedRegions': ['us-east-1', 'us-west-2'],
            'organizationStructure': {
                'security': {'name': 'Security'}
            },
            'centralizedLogging': {
                'accountId': '111111111111',
                'enabled': True
            },
            'securityRoles': {
                'accountId': '222222222222'
            }
        }
        
        result = generator.validate_manifest(valid_manifest)
        assert result is True
    
    def test_validate_manifest_missing_required_field(self, generator):
        """Test manifest validation with missing required field."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}}
            # Missing centralizedLogging and securityRoles
        }
        
        with pytest.raises(ManifestValidationError, match="Missing required field: centralizedLogging"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_governed_regions_empty(self, generator):
        """Test validation with empty governed regions."""
        invalid_manifest = {
            'governedRegions': [],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ManifestValidationError, match="governedRegions cannot be empty"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_governed_regions_invalid_format(self, generator):
        """Test validation with invalid region format."""
        invalid_manifest = {
            'governedRegions': ['us-east-1', 'invalid'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ManifestValidationError, match="Invalid region format: invalid"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_organization_structure_missing_security(self, generator):
        """Test validation with missing security OU."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'sandbox': {'name': 'Sandbox'}},  # Missing security
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ManifestValidationError, match="organizationStructure must contain 'security' OU"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_organization_structure_invalid_security_ou(self, generator):
        """Test validation with invalid security OU structure."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {}},  # Missing name
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ManifestValidationError, match="Security OU must have a 'name' field"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_centralized_logging_missing_account_id(self, generator):
        """Test validation with missing logging account ID."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'enabled': True},  # Missing accountId
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ManifestValidationError, match="centralizedLogging must contain 'accountId'"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_centralized_logging_invalid_account_id(self, generator):
        """Test validation with invalid logging account ID format."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': 'invalid'},  # Invalid format
            'securityRoles': {'accountId': '222222222222'}
        }
        
        with pytest.raises(ManifestValidationError, match="Invalid account ID format: invalid"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_security_roles_missing_account_id(self, generator):
        """Test validation with missing security account ID."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {}  # Missing accountId
        }
        
        with pytest.raises(ManifestValidationError, match="securityRoles must contain 'accountId'"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_security_roles_invalid_account_id(self, generator):
        """Test validation with invalid security account ID format."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '12345'}  # Invalid format
        }
        
        with pytest.raises(ManifestValidationError, match="Invalid account ID format: 12345"):
            generator.validate_manifest(invalid_manifest)
    
    def test_validate_account_uniqueness_same_accounts(self, generator):
        """Test validation with same account IDs for logging and security."""
        invalid_manifest = {
            'governedRegions': ['us-east-1'],
            'organizationStructure': {'security': {'name': 'Security'}},
            'centralizedLogging': {'accountId': '111111111111'},
            'securityRoles': {'accountId': '111111111111'}  # Same as logging
        }
        
        with pytest.raises(ManifestValidationError, match="centralizedLogging and securityRoles must use different account IDs"):
            generator.validate_manifest(invalid_manifest)
    
    def test_build_organization_structure(self, generator):
        """Test organization structure building."""
        org_structure = generator._build_organization_structure()
        
        expected_structure = {
            'security': {'name': 'Security'},
            'sandbox': {'name': 'Sandbox'}
        }
        
        assert org_structure == expected_structure
    
    def test_build_centralized_logging_basic(self, generator):
        """Test basic centralized logging configuration."""
        # Ensure no optional attributes exist
        if hasattr(generator.config.logging, 'retention_days'):
            delattr(generator.config.logging, 'retention_days')
        if hasattr(generator.config.logging, 'kms_key_arn'):
            delattr(generator.config.logging, 'kms_key_arn')
        
        account_ids = {'Log Archive': '111111111111'}
        
        logging_config = generator._build_centralized_logging(account_ids)
        
        expected_config = {
            'accountId': '111111111111',
            'enabled': True
        }
        
        assert logging_config == expected_config
    
    def test_build_centralized_logging_with_retention(self, generator):
        """Test centralized logging with retention configuration."""
        # Remove kms_key_arn if it exists
        if hasattr(generator.config.logging, 'kms_key_arn'):
            delattr(generator.config.logging, 'kms_key_arn')
        
        # Add retention configuration to mock config
        generator.config.logging.retention_days = 365
        
        account_ids = {'Log Archive': '111111111111'}
        
        logging_config = generator._build_centralized_logging(account_ids)
        
        expected_config = {
            'accountId': '111111111111',
            'enabled': True,
            'configurations': {
                'loggingBucket': {'retentionDays': 365},
                'accessLoggingBucket': {'retentionDays': 365}
            }
        }
        
        assert logging_config == expected_config
    
    def test_build_centralized_logging_with_kms(self, generator):
        """Test centralized logging with KMS configuration."""
        # Remove retention_days if it exists
        if hasattr(generator.config.logging, 'retention_days'):
            delattr(generator.config.logging, 'retention_days')
        
        # Add KMS configuration to mock config
        generator.config.logging.kms_key_arn = 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'
        
        account_ids = {'Log Archive': '111111111111'}
        
        logging_config = generator._build_centralized_logging(account_ids)
        
        expected_config = {
            'accountId': '111111111111',
            'enabled': True,
            'configurations': {
                'kmsKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'
            }
        }
        
        assert logging_config == expected_config
    
    def test_build_security_roles(self, generator):
        """Test security roles configuration building."""
        account_ids = {'Audit': '222222222222'}
        
        security_config = generator._build_security_roles(account_ids)
        
        expected_config = {
            'accountId': '222222222222'
        }
        
        assert security_config == expected_config
