"""AWS Organizations management for Control Tower prerequisites.

This module handles AWS Organizations setup including enabling all features,
creating organizational units, and validating organization structure for
Control Tower deployment.
"""

from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

from ..core.aws_client import AWSClientManager


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
