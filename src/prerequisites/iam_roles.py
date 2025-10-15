"""IAM roles management for Control Tower prerequisites.

This module handles validation and management of IAM roles required
for Control Tower deployment.
"""

from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

from src.core.aws_client import AWSClientManager


class IAMRoleError(Exception):
    """Base exception for IAM role operations."""
    pass


class IAMRolesManager:
    """Manages IAM roles for Control Tower deployment.
    
    Control Tower creates required roles automatically during setup.
    This class validates role existence and configuration.
    """
    
    # Control Tower automatically creates these roles
    CONTROL_TOWER_ROLES = {
        'AWSControlTowerAdmin': {
            'description': 'Administrative role for Control Tower operations',
            'trust_service': 'controltower.amazonaws.com'
        },
        'AWSControlTowerStackSetRole': {
            'description': 'CloudFormation StackSet operations role',
            'trust_service': 'cloudformation.amazonaws.com'
        },
        'AWSControlTowerCloudTrailRole': {
            'description': 'CloudTrail logging role',
            'trust_service': 'cloudtrail.amazonaws.com'
        }
    }
    
    def __init__(self, aws_client: AWSClientManager) -> None:
        """Initialize IAM roles manager.
        
        Args:
            aws_client: Configured AWS client manager
        """
        self.aws_client = aws_client
        self._iam_client = None
        
    def _get_client(self):
        """Get IAM client with caching.
        
        Returns:
            Configured IAM client
        """
        if self._iam_client is None:
            self._iam_client = self.aws_client.get_client(
                'iam',
                self.aws_client.get_current_region()
            )
        return self._iam_client
        
    def validate_control_tower_roles(self) -> Dict[str, bool]:
        """Validate Control Tower required roles exist.
        
        Returns:
            Dictionary mapping role names to existence status
        """
        results = {}
        
        for role_name in self.CONTROL_TOWER_ROLES:
            results[role_name] = self.role_exists(role_name)
            
        return results
        
    def role_exists(self, role_name: str) -> bool:
        """Check if IAM role exists.
        
        Args:
            role_name: Name of the role to check
            
        Returns:
            True if role exists, False otherwise
        """
        try:
            client = self._get_client()
            client.get_role(RoleName=role_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                return False
            raise IAMRoleError(f"Failed to check role {role_name}: {e}")
            
    def get_role_details(self, role_name: str) -> Optional[Dict[str, Any]]:
        """Get IAM role details.
        
        Args:
            role_name: Name of the role
            
        Returns:
            Role details dictionary or None if not found
        """
        try:
            client = self._get_client()
            response = client.get_role(RoleName=role_name)
            return response['Role']
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                return None
            raise IAMRoleError(f"Failed to get role details: {e}")
            
    def validate_role_trust_policy(self, role_name: str) -> bool:
        """Validate role trust policy for Control Tower service.
        
        Args:
            role_name: Name of the role to validate
            
        Returns:
            True if trust policy is valid
        """
        role_details = self.get_role_details(role_name)
        if not role_details:
            return False
            
        trust_policy = role_details.get('AssumeRolePolicyDocument', {})
        statements = trust_policy.get('Statement', [])
        
        expected_service = self.CONTROL_TOWER_ROLES.get(role_name, {}).get('trust_service')
        if not expected_service:
            return True  # Unknown role, skip validation
            
        for statement in statements:
            principal = statement.get('Principal', {})
            if isinstance(principal, dict):
                service = principal.get('Service')
                if service == expected_service:
                    return True
                    
        return False
        
    def get_missing_roles(self) -> List[str]:
        """Get list of missing Control Tower roles.
        
        Returns:
            List of missing role names
        """
        missing = []
        role_status = self.validate_control_tower_roles()
        
        for role_name, exists in role_status.items():
            if not exists:
                missing.append(role_name)
                
        return missing
        
    def get_roles_summary(self) -> Dict[str, Any]:
        """Get summary of Control Tower roles status.
        
        Returns:
            Summary dictionary with role status and details
        """
        summary = {
            'total_roles': len(self.CONTROL_TOWER_ROLES),
            'existing_roles': 0,
            'missing_roles': [],
            'role_details': {}
        }
        
        for role_name in self.CONTROL_TOWER_ROLES:
            exists = self.role_exists(role_name)
            if exists:
                summary['existing_roles'] += 1
                summary['role_details'][role_name] = {
                    'exists': True,
                    'trust_policy_valid': self.validate_role_trust_policy(role_name)
                }
            else:
                summary['missing_roles'].append(role_name)
                summary['role_details'][role_name] = {
                    'exists': False,
                    'trust_policy_valid': False
                }
                
        return summary
