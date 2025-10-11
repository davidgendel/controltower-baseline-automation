"""AWS Control Tower manifest generation and validation.

This module provides the ManifestGenerator class for creating Control Tower
landing zone manifests from YAML configuration, validating manifest structure,
and resolving account IDs dynamically.
"""

import json
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

from ..core.aws_client import AWSClientManager
from ..core.config import Configuration


class ManifestValidationError(Exception):
    """Raised when manifest validation fails."""
    pass


class ManifestGenerator:
    """Generates and validates Control Tower landing zone manifests.
    
    This class creates Control Tower manifests from YAML configuration,
    validates manifest structure against AWS schemas, and resolves
    account IDs dynamically from account names.
    """
    
    def __init__(self, config: Configuration, aws_client_manager: AWSClientManager) -> None:
        """Initialize the manifest generator.
        
        Args:
            config: Configuration instance
            aws_client_manager: AWS client manager instance
        """
        self.config = config
        self.aws_client_manager = aws_client_manager
        self._organizations_client = None
    
    @property
    def organizations_client(self):
        """Get Organizations client with lazy initialization."""
        if self._organizations_client is None:
            self._organizations_client = self.aws_client_manager.get_client('organizations')
        return self._organizations_client
    
    def generate_manifest(self) -> Dict[str, Any]:
        """Generate Control Tower manifest from configuration.
        
        Returns:
            Dictionary containing the complete landing zone manifest
            
        Raises:
            ManifestValidationError: When configuration is invalid
        """
        try:
            # Resolve account IDs from configuration
            account_ids = self._resolve_account_ids()
            
            # Build base manifest structure
            manifest = {
                'governedRegions': self.config.aws.governed_regions,
                'organizationStructure': self._build_organization_structure(),
                'centralizedLogging': self._build_centralized_logging(account_ids),
                'securityRoles': self._build_security_roles(account_ids)
            }
            
            # Add optional features
            if self.config.identity_center.enabled:
                manifest['accessManagement'] = {'enabled': True}
            
            # Validate the generated manifest
            self.validate_manifest(manifest)
            
            return manifest
            
        except Exception as e:
            raise ManifestValidationError(f"Failed to generate manifest: {str(e)}")
    
    def validate_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Validate manifest against AWS schema requirements.
        
        Args:
            manifest: Landing zone manifest dictionary
            
        Returns:
            True if manifest is valid
            
        Raises:
            ManifestValidationError: When manifest validation fails
        """
        # Required fields for landing zone version 3.3
        required_fields = ['governedRegions', 'organizationStructure', 'centralizedLogging', 'securityRoles']
        
        for field in required_fields:
            if field not in manifest:
                raise ManifestValidationError(f"Missing required field: {field}")
        
        # Validate governed regions
        self._validate_governed_regions(manifest['governedRegions'])
        
        # Validate organization structure
        self._validate_organization_structure(manifest['organizationStructure'])
        
        # Validate centralized logging
        self._validate_centralized_logging(manifest['centralizedLogging'])
        
        # Validate security roles
        self._validate_security_roles(manifest['securityRoles'])
        
        # Validate account ID uniqueness
        self._validate_account_uniqueness(manifest)
        
        return True
    
    def resolve_account_ids(self, account_names: List[str]) -> Dict[str, str]:
        """Resolve account names to account IDs.
        
        Args:
            account_names: List of account names to resolve
            
        Returns:
            Dictionary mapping account names to account IDs
            
        Raises:
            ManifestValidationError: When account resolution fails
        """
        account_mapping = {}
        
        try:
            # List all accounts in the organization
            paginator = self.organizations_client.get_paginator('list_accounts')
            
            for page in paginator.paginate():
                for account in page['Accounts']:
                    account_name = account['Name']
                    account_id = account['Id']
                    
                    if account_name in account_names:
                        account_mapping[account_name] = account_id
            
            # Check if all requested accounts were found
            missing_accounts = set(account_names) - set(account_mapping.keys())
            if missing_accounts:
                raise ManifestValidationError(
                    f"Could not find accounts: {', '.join(missing_accounts)}"
                )
            
            return account_mapping
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            raise ManifestValidationError(f"Failed to resolve account IDs: {error_message}")
    
    def _resolve_account_ids(self) -> Dict[str, str]:
        """Resolve account IDs from configuration."""
        account_names = [
            self.config.accounts.log_archive.name,
            self.config.accounts.audit.name
        ]
        
        return self.resolve_account_ids(account_names)
    
    def _build_organization_structure(self) -> Dict[str, Any]:
        """Build organization structure from configuration."""
        org_structure = {
            'security': {
                'name': self.config.organization.security_ou_name
            }
        }
        
        # Add additional OUs if configured
        for ou_config in self.config.organization.additional_ous:
            ou_name = ou_config['name']
            org_structure[ou_name.lower()] = {
                'name': ou_name
            }
        
        return org_structure
    
    def _build_centralized_logging(self, account_ids: Dict[str, str]) -> Dict[str, Any]:
        """Build centralized logging configuration."""
        log_account_name = self.config.accounts.log_archive.name
        log_account_id = account_ids[log_account_name]
        
        centralized_logging = {
            'accountId': log_account_id,
            'enabled': self.config.logging.cloudtrail_enabled
        }
        
        # Add optional configurations if specified
        configurations = {}
        
        # Add log retention if specified in config
        if hasattr(self.config.logging, 'retention_days') and self.config.logging.retention_days is not None:
            configurations['loggingBucket'] = {
                'retentionDays': self.config.logging.retention_days
            }
            configurations['accessLoggingBucket'] = {
                'retentionDays': self.config.logging.retention_days
            }
        
        # Add KMS key if specified
        if hasattr(self.config.logging, 'kms_key_arn') and self.config.logging.kms_key_arn:
            configurations['kmsKeyArn'] = self.config.logging.kms_key_arn
        
        if configurations:
            centralized_logging['configurations'] = configurations
        
        return centralized_logging
    
    def _build_security_roles(self, account_ids: Dict[str, str]) -> Dict[str, Any]:
        """Build security roles configuration."""
        audit_account_name = self.config.accounts.audit.name
        audit_account_id = account_ids[audit_account_name]
        
        return {
            'accountId': audit_account_id
        }
    
    def _validate_governed_regions(self, governed_regions: List[str]) -> None:
        """Validate governed regions configuration."""
        if not isinstance(governed_regions, list):
            raise ManifestValidationError("governedRegions must be a list")
        
        if not governed_regions:
            raise ManifestValidationError("governedRegions cannot be empty")
        
        # Validate region format (basic check)
        for region in governed_regions:
            if not isinstance(region, str) or len(region) < 9:
                raise ManifestValidationError(f"Invalid region format: {region}")
    
    def _validate_organization_structure(self, org_structure: Dict[str, Any]) -> None:
        """Validate organization structure configuration."""
        if not isinstance(org_structure, dict):
            raise ManifestValidationError("organizationStructure must be a dictionary")
        
        if 'security' not in org_structure:
            raise ManifestValidationError("organizationStructure must contain 'security' OU")
        
        # Validate security OU structure
        security_ou = org_structure['security']
        if not isinstance(security_ou, dict) or 'name' not in security_ou:
            raise ManifestValidationError("Security OU must have a 'name' field")
    
    def _validate_centralized_logging(self, centralized_logging: Dict[str, Any]) -> None:
        """Validate centralized logging configuration."""
        if not isinstance(centralized_logging, dict):
            raise ManifestValidationError("centralizedLogging must be a dictionary")
        
        if 'accountId' not in centralized_logging:
            raise ManifestValidationError("centralizedLogging must contain 'accountId'")
        
        # Validate account ID format (12 digits)
        account_id = centralized_logging['accountId']
        if not isinstance(account_id, str) or len(account_id) != 12 or not account_id.isdigit():
            raise ManifestValidationError(f"Invalid account ID format: {account_id}")
    
    def _validate_security_roles(self, security_roles: Dict[str, Any]) -> None:
        """Validate security roles configuration."""
        if not isinstance(security_roles, dict):
            raise ManifestValidationError("securityRoles must be a dictionary")
        
        if 'accountId' not in security_roles:
            raise ManifestValidationError("securityRoles must contain 'accountId'")
        
        # Validate account ID format (12 digits)
        account_id = security_roles['accountId']
        if not isinstance(account_id, str) or len(account_id) != 12 or not account_id.isdigit():
            raise ManifestValidationError(f"Invalid account ID format: {account_id}")
    
    def _validate_account_uniqueness(self, manifest: Dict[str, Any]) -> None:
        """Validate that different account IDs are used for different purposes."""
        log_account_id = manifest['centralizedLogging']['accountId']
        security_account_id = manifest['securityRoles']['accountId']
        
        if log_account_id == security_account_id:
            raise ManifestValidationError(
                "centralizedLogging and securityRoles must use different account IDs"
            )
