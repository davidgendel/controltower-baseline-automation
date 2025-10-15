"""AWS Organizations management for Control Tower prerequisites.

This module handles AWS Organizations setup including creating organizations,
enabling all features, creating organizational units, and validating 
organization structure for Control Tower deployment.
"""

import time
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

from src.core.aws_client import AWSClientManager


class OrganizationsError(Exception):
    """Base exception for Organizations operations."""
    pass


class DuplicateOUError(OrganizationsError):
    """Raised when attempting to create a duplicate OU."""
    pass


class OrganizationsManager:
    """Manages AWS Organizations setup for Control Tower prerequisites.
    
    This class handles enabling all features, creating organizational units,
    and validating organization structure for Control Tower deployment.
    """
    
    def __init__(self, aws_client: AWSClientManager) -> None:
        """Initialize Organizations manager.
        
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
        
    def create_organization(self) -> Dict[str, Any]:
        """Create AWS Organization with all features enabled.
        
        Returns:
            Dictionary containing created organization details
            
        Raises:
            OrganizationsError: When creation fails
        """
        try:
            client = self._get_client()
            
            # Create organization with all features enabled
            response = client.create_organization(FeatureSet='ALL')
            organization = response['Organization']
            
            print(f"  ✅ Organization created with ID: {organization['Id']}")
            print(f"  ✅ Management Account: {organization['MasterAccountId']}")
            
            return organization
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AlreadyInOrganizationException':
                # Organization already exists, get details
                return self.get_organization_info()
            elif error_code == 'AccessDeniedForDependencyException':
                raise OrganizationsError(
                    "Missing required permission: iam:CreateServiceLinkedRole for organizations.amazonaws.com"
                )
            elif error_code == 'ConstraintViolationException':
                error_message = e.response['Error']['Message']
                if 'ACCOUNT_CREATION_NOT_COMPLETE' in error_message:
                    raise OrganizationsError(
                        "Account setup is not complete. Please complete account setup before creating an organization."
                    )
                else:
                    raise OrganizationsError(f"Organization creation constraint violation: {error_message}")
            else:
                raise OrganizationsError(f"Failed to create organization: {e}")
    
    def wait_for_organization_ready(self, max_wait_seconds: int = 300) -> bool:
        """Wait for organization to be fully ready after creation.
        
        Args:
            max_wait_seconds: Maximum time to wait in seconds
            
        Returns:
            True if organization is ready, False if timeout
        """
        print("  ⏳ Waiting for organization to be fully ready...")
        
        # Initial wait of 60 seconds as requested
        print("  ⏳ Initial wait: 60 seconds...")
        time.sleep(60)
        
        start_time = time.time()
        check_interval = 30  # Check every 30 seconds after initial wait
        
        while (time.time() - start_time) < max_wait_seconds:
            try:
                # Check if we can successfully describe the organization
                org_info = self.get_organization_info()
                
                # Verify organization is in a stable state
                if org_info.get('FeatureSet') == 'ALL':
                    print("  ✅ Organization is ready")
                    return True
                    
            except OrganizationsError:
                # Organization not ready yet, continue waiting
                pass
            
            print(f"  ⏳ Checking again in {check_interval} seconds...")
            time.sleep(check_interval)
        
        print("  ⚠️ Timeout waiting for organization to be ready")
        return False
    
    def organization_exists(self) -> bool:
        """Check if AWS Organization exists.
        
        Returns:
            True if organization exists, False otherwise
        """
        try:
            self.get_organization_info()
            return True
        except OrganizationsError:
            return False
    
    def find_account_by_email(self, email: str) -> Optional[str]:
        """Find account ID by email address.
        
        Args:
            email: Account email address to search for
            
        Returns:
            Account ID if found, None otherwise
        """
        try:
            client = self._get_client()
            
            # List all accounts in the organization
            paginator = client.get_paginator('list_accounts')
            
            for page in paginator.paginate():
                for account in page['Accounts']:
                    if account.get('Email', '').lower() == email.lower():
                        return account['Id']
            
            return None
            
        except ClientError:
            return None
    
    def find_account_by_name(self, name: str) -> Optional[str]:
        """Find account ID by account name.
        
        Args:
            name: Account name to search for
            
        Returns:
            Account ID if found, None otherwise
        """
        try:
            client = self._get_client()
            
            # List all accounts in the organization
            paginator = client.get_paginator('list_accounts')
            
            for page in paginator.paginate():
                for account in page['Accounts']:
                    if account.get('Name', '').lower() == name.lower():
                        return account['Id']
            
            return None
            
        except ClientError:
            return None
    
    def validate_account_in_security_ou(self, account_id: str) -> bool:
        """Validate that account is in Security OU.
        
        Args:
            account_id: Account ID to validate
            
        Returns:
            True if account is in Security OU, False otherwise
        """
        try:
            client = self._get_client()
            
            # Get root ID
            root_id = self.get_root_id()
            
            # List OUs under root
            ous = self.list_organizational_units(root_id)
            
            # Find Security OU
            security_ou_id = None
            for ou in ous:
                if ou['Name'].lower() == 'security':
                    security_ou_id = ou['Id']
                    break
            
            if not security_ou_id:
                return False
            
            # List accounts in Security OU
            response = client.list_accounts_for_parent(ParentId=security_ou_id)
            
            for account in response['Accounts']:
                if account['Id'] == account_id:
                    return True
            
            return False
            
        except ClientError:
            return False
    
    def enable_all_features(self) -> bool:
        """Enable all features in AWS Organizations.
        
        Returns:
            True if all features are enabled, False otherwise
            
        Raises:
            OrganizationsError: When enable operation fails
        """
        try:
            client = self._get_client()
            
            # Check current feature set
            org_info = client.describe_organization()
            current_features = org_info['Organization']['FeatureSet']
            
            if current_features == 'ALL':
                return True
                
            # Enable all features
            client.enable_all_features()
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConcurrentModificationException':
                raise OrganizationsError(
                    "Organization is being modified. Please wait and try again."
                )
            elif error_code == 'HandshakeConstraintViolationException':
                raise OrganizationsError(
                    "Cannot enable all features due to pending invitations. "
                    "Accept or decline all pending invitations first."
                )
            else:
                raise OrganizationsError(f"Failed to enable all features: {e}")
                
    def get_organization_info(self) -> Dict[str, Any]:
        """Get organization information.
        
        Returns:
            Dictionary containing organization details
            
        Raises:
            OrganizationsError: When unable to get organization info
        """
        try:
            client = self._get_client()
            response = client.describe_organization()
            return response['Organization']
        except ClientError as e:
            raise OrganizationsError(f"Failed to get organization info: {e}")
            
    def list_organizational_units(self, parent_id: str) -> List[Dict[str, Any]]:
        """List organizational units under a parent.
        
        Args:
            parent_id: ID of the parent (root or OU)
            
        Returns:
            List of organizational unit details
            
        Raises:
            OrganizationsError: When unable to list OUs
        """
        try:
            client = self._get_client()
            response = client.list_organizational_units_for_parent(
                ParentId=parent_id
            )
            return response['OrganizationalUnits']
        except ClientError as e:
            raise OrganizationsError(f"Failed to list OUs: {e}")
            
    def create_organizational_unit(self, name: str, 
                                  parent_id: str) -> Dict[str, Any]:
        """Create an organizational unit.
        
        Args:
            name: Name of the organizational unit
            parent_id: ID of the parent (root or OU)
            
        Returns:
            Dictionary containing created OU details
            
        Raises:
            DuplicateOUError: When OU already exists
            OrganizationsError: When creation fails
        """
        try:
            # Check if OU already exists
            existing_ous = self.list_organizational_units(parent_id)
            for ou in existing_ous:
                if ou['Name'] == name:
                    raise DuplicateOUError(
                        f"Organizational unit '{name}' already exists"
                    )
                    
            # Create the OU
            client = self._get_client()
            response = client.create_organizational_unit(
                ParentId=parent_id,
                Name=name
            )
            return response['OrganizationalUnit']
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DuplicateOrganizationalUnitException':
                raise DuplicateOUError(
                    f"Organizational unit '{name}' already exists"
                )
            else:
                raise OrganizationsError(f"Failed to create OU '{name}': {e}")
                
    def get_root_id(self) -> str:
        """Get the root ID of the organization.
        
        Returns:
            Root ID string
            
        Raises:
            OrganizationsError: When unable to get root ID
        """
        try:
            client = self._get_client()
            response = client.list_roots()
            roots = response['Roots']
            
            if not roots:
                raise OrganizationsError("No roots found in organization")
                
            return roots[0]['Id']
            
        except ClientError as e:
            raise OrganizationsError(f"Failed to get root ID: {e}")
            
    def validate_organization_structure(self) -> Dict[str, Any]:
        """Validate organization structure for Control Tower.
        
        Returns:
            Dictionary containing validation results
        """
        results = {
            'valid': True,
            'issues': [],
            'organization_info': {},
            'root_id': None,
            'security_ou': None,
            'sandbox_ou': None
        }
        
        try:
            # Get organization info
            org_info = self.get_organization_info()
            results['organization_info'] = org_info
            
            # Check if all features are enabled
            if org_info['FeatureSet'] != 'ALL':
                results['valid'] = False
                results['issues'].append(
                    "Organization does not have all features enabled"
                )
                
            # Get root ID
            root_id = self.get_root_id()
            results['root_id'] = root_id
            
            # Check for required OUs
            ous = self.list_organizational_units(root_id)
            ou_names = {ou['Name']: ou for ou in ous}
            
            if 'Security' in ou_names:
                results['security_ou'] = ou_names['Security']
            else:
                results['issues'].append("Security OU not found")
                
            if 'Sandbox' in ou_names:
                results['sandbox_ou'] = ou_names['Sandbox']
            else:
                results['issues'].append("Sandbox OU not found")
                
        except OrganizationsError as e:
            results['valid'] = False
            results['issues'].append(str(e))
            
        return results
