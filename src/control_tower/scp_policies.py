"""AWS Control Tower SCP policy management.

This module provides the SCPPolicyManager class for managing Service Control
Policies (SCPs) with three security tiers: Basic, Standard, and Strict.
"""

import json
import os
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

from ..core.aws_client import AWSClientManager


class SCPPolicyError(Exception):
    """Raised when SCP policy operations fail."""
    pass


class SCPPolicyManager:
    """Manages AWS Organizations Service Control Policies.
    
    This class handles SCP policy deployment and attachment with three
    predefined security tiers: Basic, Standard, and Strict.
    """
    
    # SCP tier definitions
    SCP_TIERS = {
        'basic': 'Basic Security Tier - Minimal restrictions for development',
        'standard': 'Standard Security Tier - Balanced security for production',
        'strict': 'Strict Security Tier - Maximum security for compliance'
    }
    
    def __init__(self, aws_client_manager: AWSClientManager) -> None:
        """Initialize the SCP policy manager.
        
        Args:
            aws_client_manager: AWS client manager instance
        """
        self.aws_client_manager = aws_client_manager
        self._organizations_client = None
    
    @property
    def organizations_client(self):
        """Get Organizations client with lazy initialization."""
        if self._organizations_client is None:
            self._organizations_client = self.aws_client_manager.get_client('organizations')
        return self._organizations_client
    
    def deploy_scp_tier(self, tier: str, target_ou_ids: List[str]) -> Dict[str, List[str]]:
        """Deploy SCP tier policies to specified OUs.
        
        Args:
            tier: SCP tier name (basic, standard, strict)
            target_ou_ids: List of OU IDs to attach policies to
            
        Returns:
            Dictionary mapping policy names to their IDs
            
        Raises:
            SCPPolicyError: When deployment fails
        """
        if tier not in self.SCP_TIERS:
            raise SCPPolicyError(f"Invalid SCP tier: {tier}. Valid tiers: {list(self.SCP_TIERS.keys())}")
        
        try:
            # Load tier configuration
            tier_config = self._load_tier_config(tier)
            
            # Validate policies before deployment
            self.validate_scp_policies(tier_config['policies'])
            
            # Deploy policies
            deployed_policies = {}
            
            for policy_config in tier_config['policies']:
                policy_name = f"ControlTower-{tier.title()}-{policy_config['name']}"
                policy_document = json.dumps(policy_config['policy'])
                
                # Create or update policy
                policy_id = self._create_or_update_policy(policy_name, policy_document, policy_config['description'])
                deployed_policies[policy_name] = policy_id
                
                # Attach policy to target OUs
                for ou_id in target_ou_ids:
                    self._attach_policy_to_ou(policy_id, ou_id)
                
                print(f"✓ Deployed SCP policy: {policy_name}")
            
            print(f"✅ Successfully deployed {tier} SCP tier ({len(deployed_policies)} policies)")
            return deployed_policies
            
        except Exception as e:
            raise SCPPolicyError(f"Failed to deploy SCP tier '{tier}': {str(e)}")
    
    def validate_scp_policies(self, policies: List[Dict[str, Any]]) -> bool:
        """Validate SCP policies before deployment.
        
        Args:
            policies: List of policy configurations
            
        Returns:
            True if all policies are valid
            
        Raises:
            SCPPolicyError: When validation fails
        """
        for policy_config in policies:
            # Check required fields
            required_fields = ['name', 'description', 'policy']
            for field in required_fields:
                if field not in policy_config:
                    raise SCPPolicyError(f"Missing required field '{field}' in policy configuration")
            
            # Validate policy document structure
            policy_doc = policy_config['policy']
            if not isinstance(policy_doc, dict):
                raise SCPPolicyError(f"Policy document must be a dictionary for policy: {policy_config['name']}")
            
            if 'Version' not in policy_doc:
                raise SCPPolicyError(f"Policy document missing 'Version' field for policy: {policy_config['name']}")
            
            if 'Statement' not in policy_doc:
                raise SCPPolicyError(f"Policy document missing 'Statement' field for policy: {policy_config['name']}")
            
            # Validate policy size (AWS limit: 5120 characters)
            policy_json = json.dumps(policy_doc)
            if len(policy_json) > 5120:
                raise SCPPolicyError(f"Policy document too large ({len(policy_json)} chars) for policy: {policy_config['name']}")
        
        return True
    
    def attach_policies_to_ou(self, policy_ids: List[str], ou_id: str) -> None:
        """Attach multiple policies to an OU.
        
        Args:
            policy_ids: List of policy IDs to attach
            ou_id: Target OU ID
            
        Raises:
            SCPPolicyError: When attachment fails
        """
        try:
            for policy_id in policy_ids:
                self._attach_policy_to_ou(policy_id, ou_id)
            
            print(f"✓ Attached {len(policy_ids)} policies to OU: {ou_id}")
            
        except Exception as e:
            raise SCPPolicyError(f"Failed to attach policies to OU {ou_id}: {str(e)}")
    
    def list_existing_policies(self) -> List[Dict[str, Any]]:
        """List existing SCP policies in the organization.
        
        Returns:
            List of policy information dictionaries
            
        Raises:
            SCPPolicyError: When listing fails
        """
        try:
            policies = []
            paginator = self.organizations_client.get_paginator('list_policies')
            
            for page in paginator.paginate(Filter='SERVICE_CONTROL_POLICY'):
                for policy in page['Policies']:
                    policies.append({
                        'id': policy['Id'],
                        'name': policy['Name'],
                        'description': policy.get('Description', ''),
                        'aws_managed': policy['AwsManaged']
                    })
            
            return policies
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            raise SCPPolicyError(f"Failed to list existing policies: {error_message}")
    
    def cleanup_policies(self, policy_name_prefix: str) -> int:
        """Clean up policies with specified name prefix.
        
        Args:
            policy_name_prefix: Prefix to match for policy cleanup
            
        Returns:
            Number of policies cleaned up
            
        Raises:
            SCPPolicyError: When cleanup fails
        """
        try:
            existing_policies = self.list_existing_policies()
            cleanup_count = 0
            
            for policy in existing_policies:
                if policy['name'].startswith(policy_name_prefix) and not policy['aws_managed']:
                    # Detach policy from all targets first
                    self._detach_policy_from_all_targets(policy['id'])
                    
                    # Delete the policy
                    self.organizations_client.delete_policy(PolicyId=policy['id'])
                    cleanup_count += 1
                    print(f"✓ Cleaned up policy: {policy['name']}")
            
            if cleanup_count > 0:
                print(f"✅ Cleaned up {cleanup_count} policies")
            
            return cleanup_count
            
        except Exception as e:
            raise SCPPolicyError(f"Failed to cleanup policies: {str(e)}")
    
    def _load_tier_config(self, tier: str) -> Dict[str, Any]:
        """Load SCP tier configuration from file."""
        config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'scp-tiers')
        config_file = os.path.join(config_dir, f'{tier}.json')
        
        if not os.path.exists(config_file):
            raise SCPPolicyError(f"SCP tier configuration file not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise SCPPolicyError(f"Invalid JSON in SCP tier configuration: {str(e)}")
    
    def _create_or_update_policy(self, name: str, policy_document: str, description: str) -> str:
        """Create or update an SCP policy."""
        try:
            # Check if policy already exists
            existing_policies = self.list_existing_policies()
            existing_policy = next((p for p in existing_policies if p['name'] == name), None)
            
            if existing_policy:
                # Update existing policy
                response = self.organizations_client.update_policy(
                    PolicyId=existing_policy['id'],
                    Name=name,
                    Description=description,
                    Content=policy_document
                )
                return response['Policy']['PolicySummary']['Id']
            else:
                # Create new policy
                response = self.organizations_client.create_policy(
                    Name=name,
                    Description=description,
                    Type='SERVICE_CONTROL_POLICY',
                    Content=policy_document
                )
                return response['Policy']['PolicySummary']['Id']
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'PolicyInUseException':
                raise SCPPolicyError(f"Policy is in use and cannot be updated: {name}")
            elif error_code == 'DuplicatePolicyException':
                raise SCPPolicyError(f"Policy with same name already exists: {name}")
            else:
                raise SCPPolicyError(f"Failed to create/update policy '{name}': {error_message}")
    
    def _attach_policy_to_ou(self, policy_id: str, ou_id: str) -> None:
        """Attach a policy to an OU."""
        try:
            self.organizations_client.attach_policy(
                PolicyId=policy_id,
                TargetId=ou_id
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'DuplicatePolicyAttachmentException':
                # Policy already attached, this is OK
                pass
            elif error_code == 'PolicyNotAttachableException':
                raise SCPPolicyError(f"Policy cannot be attached to OU: {error_message}")
            else:
                raise SCPPolicyError(f"Failed to attach policy to OU: {error_message}")
    
    def _detach_policy_from_all_targets(self, policy_id: str) -> None:
        """Detach a policy from all its targets."""
        try:
            # List targets for the policy
            paginator = self.organizations_client.get_paginator('list_targets_for_policy')
            
            for page in paginator.paginate(PolicyId=policy_id):
                for target in page['Targets']:
                    try:
                        self.organizations_client.detach_policy(
                            PolicyId=policy_id,
                            TargetId=target['TargetId']
                        )
                    except ClientError as e:
                        # Continue with other targets if one fails
                        print(f"⚠️  Failed to detach policy from target {target['TargetId']}: {e}")
                        
        except ClientError as e:
            # Don't fail cleanup if we can't list targets
            print(f"⚠️  Failed to list targets for policy {policy_id}: {e}")
