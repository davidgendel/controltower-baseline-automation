"""Tests for SCP policy management functionality."""

import pytest
import json
import os
from unittest.mock import Mock, patch, mock_open
from botocore.exceptions import ClientError

from src.control_tower.scp_policies import SCPPolicyManager, SCPPolicyError
from src.core.aws_client import AWSClientManager


class TestSCPPolicyManager:
    """Test cases for SCPPolicyManager class."""
    
    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create mock AWS client manager."""
        manager = Mock(spec=AWSClientManager)
        mock_client = Mock()
        manager.get_client.return_value = mock_client
        return manager
    
    @pytest.fixture
    def scp_manager(self, mock_aws_client_manager):
        """Create SCPPolicyManager instance."""
        return SCPPolicyManager(mock_aws_client_manager)
    
    @pytest.fixture
    def mock_tier_config(self):
        """Create mock tier configuration."""
        return {
            "name": "Test Security Tier",
            "description": "Test security tier for unit tests",
            "policies": [
                {
                    "name": "TestPolicy1",
                    "description": "Test policy 1",
                    "policy": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Sid": "TestStatement",
                                "Effect": "Deny",
                                "Principal": {"AWS": "*"},
                                "Action": "s3:DeleteBucket",
                                "Resource": "*"
                            }
                        ]
                    }
                },
                {
                    "name": "TestPolicy2",
                    "description": "Test policy 2",
                    "policy": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Sid": "TestStatement2",
                                "Effect": "Deny",
                                "Principal": {"AWS": "*"},
                                "Action": "iam:DeleteRole",
                                "Resource": "*"
                            }
                        ]
                    }
                }
            ]
        }
    
    def test_init(self, mock_aws_client_manager):
        """Test SCP manager initialization."""
        manager = SCPPolicyManager(mock_aws_client_manager)
        
        assert manager.aws_client_manager == mock_aws_client_manager
        assert manager._organizations_client is None
    
    def test_organizations_client_property(self, scp_manager, mock_aws_client_manager):
        """Test lazy initialization of Organizations client."""
        # First access should create client
        client = scp_manager.organizations_client
        mock_aws_client_manager.get_client.assert_called_once_with('organizations')
        
        # Second access should return same client
        client2 = scp_manager.organizations_client
        assert client == client2
        assert mock_aws_client_manager.get_client.call_count == 1
    
    def test_scp_tiers_constant(self):
        """Test SCP tiers constant definition."""
        expected_tiers = ['basic', 'standard', 'strict']
        assert all(tier in SCPPolicyManager.SCP_TIERS for tier in expected_tiers)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_deploy_scp_tier_success(self, mock_exists, mock_file, scp_manager, mock_tier_config):
        """Test successful SCP tier deployment."""
        # Mock file operations
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(mock_tier_config)
        
        # Mock Organizations API responses
        scp_manager.organizations_client.list_policies.return_value = {'Policies': []}
        scp_manager.organizations_client.create_policy.side_effect = [
            {'Policy': {'PolicySummary': {'Id': 'policy-1'}}},
            {'Policy': {'PolicySummary': {'Id': 'policy-2'}}}
        ]
        scp_manager.organizations_client.attach_policy.return_value = {}
        
        # Mock paginator
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{'Policies': []}]
        scp_manager.organizations_client.get_paginator.return_value = mock_paginator
        
        target_ous = ['ou-12345', 'ou-67890']
        result = scp_manager.deploy_scp_tier('basic', target_ous)
        
        # Verify results
        assert len(result) == 2
        assert 'ControlTower-Basic-TestPolicy1' in result
        assert 'ControlTower-Basic-TestPolicy2' in result
        
        # Verify API calls
        assert scp_manager.organizations_client.create_policy.call_count == 2
        assert scp_manager.organizations_client.attach_policy.call_count == 4  # 2 policies × 2 OUs
    
    def test_deploy_scp_tier_invalid_tier(self, scp_manager):
        """Test deployment with invalid tier."""
        with pytest.raises(SCPPolicyError, match="Invalid SCP tier: invalid"):
            scp_manager.deploy_scp_tier('invalid', ['ou-12345'])
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_deploy_scp_tier_file_not_found(self, mock_exists, mock_file, scp_manager):
        """Test deployment with missing configuration file."""
        mock_exists.return_value = False
        
        with pytest.raises(SCPPolicyError, match="SCP tier configuration file not found"):
            scp_manager.deploy_scp_tier('basic', ['ou-12345'])
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_deploy_scp_tier_invalid_json(self, mock_exists, mock_file, scp_manager):
        """Test deployment with invalid JSON configuration."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        
        with pytest.raises(SCPPolicyError, match="Invalid JSON in SCP tier configuration"):
            scp_manager.deploy_scp_tier('basic', ['ou-12345'])
    
    def test_validate_scp_policies_success(self, scp_manager, mock_tier_config):
        """Test successful policy validation."""
        result = scp_manager.validate_scp_policies(mock_tier_config['policies'])
        assert result is True
    
    def test_validate_scp_policies_missing_field(self, scp_manager):
        """Test policy validation with missing required field."""
        invalid_policies = [
            {
                "name": "TestPolicy",
                "policy": {"Version": "2012-10-17", "Statement": []}
                # Missing description
            }
        ]
        
        with pytest.raises(SCPPolicyError, match="Missing required field 'description'"):
            scp_manager.validate_scp_policies(invalid_policies)
    
    def test_validate_scp_policies_invalid_policy_document(self, scp_manager):
        """Test policy validation with invalid policy document."""
        invalid_policies = [
            {
                "name": "TestPolicy",
                "description": "Test policy",
                "policy": "not a dictionary"
            }
        ]
        
        with pytest.raises(SCPPolicyError, match="Policy document must be a dictionary"):
            scp_manager.validate_scp_policies(invalid_policies)
    
    def test_validate_scp_policies_missing_version(self, scp_manager):
        """Test policy validation with missing Version field."""
        invalid_policies = [
            {
                "name": "TestPolicy",
                "description": "Test policy",
                "policy": {
                    "Statement": []
                    # Missing Version
                }
            }
        ]
        
        with pytest.raises(SCPPolicyError, match="Policy document missing 'Version' field"):
            scp_manager.validate_scp_policies(invalid_policies)
    
    def test_validate_scp_policies_missing_statement(self, scp_manager):
        """Test policy validation with missing Statement field."""
        invalid_policies = [
            {
                "name": "TestPolicy",
                "description": "Test policy",
                "policy": {
                    "Version": "2012-10-17"
                    # Missing Statement
                }
            }
        ]
        
        with pytest.raises(SCPPolicyError, match="Policy document missing 'Statement' field"):
            scp_manager.validate_scp_policies(invalid_policies)
    
    def test_validate_scp_policies_too_large(self, scp_manager):
        """Test policy validation with oversized policy."""
        # Create a policy that exceeds 5120 characters
        large_statement = {
            "Sid": "LargeStatement",
            "Effect": "Deny",
            "Principal": {"AWS": "*"},
            "Action": ["s3:*"] * 1000,  # Large action list
            "Resource": "*"
        }
        
        invalid_policies = [
            {
                "name": "TestPolicy",
                "description": "Test policy",
                "policy": {
                    "Version": "2012-10-17",
                    "Statement": [large_statement]
                }
            }
        ]
        
        with pytest.raises(SCPPolicyError, match="Policy document too large"):
            scp_manager.validate_scp_policies(invalid_policies)
    
    def test_attach_policies_to_ou_success(self, scp_manager):
        """Test successful policy attachment to OU."""
        scp_manager.organizations_client.attach_policy.return_value = {}
        
        policy_ids = ['policy-1', 'policy-2']
        scp_manager.attach_policies_to_ou(policy_ids, 'ou-12345')
        
        assert scp_manager.organizations_client.attach_policy.call_count == 2
    
    def test_attach_policies_to_ou_failure(self, scp_manager):
        """Test policy attachment failure."""
        error_response = {
            'Error': {
                'Code': 'PolicyNotAttachableException',
                'Message': 'Policy cannot be attached'
            }
        }
        scp_manager.organizations_client.attach_policy.side_effect = ClientError(
            error_response, 'AttachPolicy'
        )
        
        with pytest.raises(SCPPolicyError, match="Failed to attach policies to OU"):
            scp_manager.attach_policies_to_ou(['policy-1'], 'ou-12345')
    
    def test_list_existing_policies_success(self, scp_manager):
        """Test successful listing of existing policies."""
        mock_response = {
            'Policies': [
                {
                    'Id': 'policy-1',
                    'Name': 'TestPolicy1',
                    'Description': 'Test policy 1',
                    'AwsManaged': False
                },
                {
                    'Id': 'policy-2',
                    'Name': 'TestPolicy2',
                    'AwsManaged': True
                }
            ]
        }
        
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [mock_response]
        scp_manager.organizations_client.get_paginator.return_value = mock_paginator
        
        policies = scp_manager.list_existing_policies()
        
        assert len(policies) == 2
        assert policies[0]['id'] == 'policy-1'
        assert policies[0]['name'] == 'TestPolicy1'
        assert policies[0]['aws_managed'] is False
        assert policies[1]['aws_managed'] is True
    
    def test_list_existing_policies_failure(self, scp_manager):
        """Test listing policies failure."""
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Insufficient permissions'
            }
        }
        scp_manager.organizations_client.get_paginator.side_effect = ClientError(
            error_response, 'ListPolicies'
        )
        
        with pytest.raises(SCPPolicyError, match="Failed to list existing policies"):
            scp_manager.list_existing_policies()
    
    def test_cleanup_policies_success(self, scp_manager):
        """Test successful policy cleanup."""
        # Mock existing policies
        existing_policies = [
            {'id': 'policy-1', 'name': 'ControlTower-Test-Policy1', 'aws_managed': False},
            {'id': 'policy-2', 'name': 'ControlTower-Test-Policy2', 'aws_managed': False},
            {'id': 'policy-3', 'name': 'OtherPolicy', 'aws_managed': False},
            {'id': 'policy-4', 'name': 'ControlTower-Test-Policy3', 'aws_managed': True}
        ]
        
        scp_manager.list_existing_policies = Mock(return_value=existing_policies)
        scp_manager._detach_policy_from_all_targets = Mock()
        scp_manager.organizations_client.delete_policy.return_value = {}
        
        cleanup_count = scp_manager.cleanup_policies('ControlTower-Test-')
        
        assert cleanup_count == 2  # Only non-AWS managed policies with prefix
        assert scp_manager.organizations_client.delete_policy.call_count == 2
    
    def test_cleanup_policies_failure(self, scp_manager):
        """Test policy cleanup failure."""
        scp_manager.list_existing_policies = Mock(side_effect=SCPPolicyError("List failed"))
        
        with pytest.raises(SCPPolicyError, match="Failed to cleanup policies"):
            scp_manager.cleanup_policies('ControlTower-')
    
    def test_create_or_update_policy_create_new(self, scp_manager):
        """Test creating a new policy."""
        # Mock no existing policies
        scp_manager.list_existing_policies = Mock(return_value=[])
        
        mock_response = {
            'Policy': {
                'PolicySummary': {
                    'Id': 'new-policy-id'
                }
            }
        }
        scp_manager.organizations_client.create_policy.return_value = mock_response
        
        policy_id = scp_manager._create_or_update_policy(
            'TestPolicy',
            '{"Version": "2012-10-17", "Statement": []}',
            'Test policy description'
        )
        
        assert policy_id == 'new-policy-id'
        scp_manager.organizations_client.create_policy.assert_called_once()
    
    def test_create_or_update_policy_update_existing(self, scp_manager):
        """Test updating an existing policy."""
        # Mock existing policy
        existing_policies = [
            {'id': 'existing-policy-id', 'name': 'TestPolicy', 'aws_managed': False}
        ]
        scp_manager.list_existing_policies = Mock(return_value=existing_policies)
        
        mock_response = {
            'Policy': {
                'PolicySummary': {
                    'Id': 'existing-policy-id'
                }
            }
        }
        scp_manager.organizations_client.update_policy.return_value = mock_response
        
        policy_id = scp_manager._create_or_update_policy(
            'TestPolicy',
            '{"Version": "2012-10-17", "Statement": []}',
            'Updated test policy description'
        )
        
        assert policy_id == 'existing-policy-id'
        scp_manager.organizations_client.update_policy.assert_called_once()
    
    def test_create_or_update_policy_duplicate_error(self, scp_manager):
        """Test policy creation with duplicate error."""
        scp_manager.list_existing_policies = Mock(return_value=[])
        
        error_response = {
            'Error': {
                'Code': 'DuplicatePolicyException',
                'Message': 'Policy already exists'
            }
        }
        scp_manager.organizations_client.create_policy.side_effect = ClientError(
            error_response, 'CreatePolicy'
        )
        
        with pytest.raises(SCPPolicyError, match="Policy with same name already exists"):
            scp_manager._create_or_update_policy('TestPolicy', '{}', 'Description')
    
    def test_attach_policy_to_ou_duplicate_attachment(self, scp_manager):
        """Test policy attachment with duplicate attachment (should not fail)."""
        error_response = {
            'Error': {
                'Code': 'DuplicatePolicyAttachmentException',
                'Message': 'Policy already attached'
            }
        }
        scp_manager.organizations_client.attach_policy.side_effect = ClientError(
            error_response, 'AttachPolicy'
        )
        
        # Should not raise exception for duplicate attachment
        scp_manager._attach_policy_to_ou('policy-1', 'ou-12345')
    
    def test_detach_policy_from_all_targets_success(self, scp_manager):
        """Test successful policy detachment from all targets."""
        mock_response = {
            'Targets': [
                {'TargetId': 'ou-12345'},
                {'TargetId': 'ou-67890'}
            ]
        }
        
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [mock_response]
        scp_manager.organizations_client.get_paginator.return_value = mock_paginator
        scp_manager.organizations_client.detach_policy.return_value = {}
        
        # Should not raise exception
        scp_manager._detach_policy_from_all_targets('policy-1')
        
        assert scp_manager.organizations_client.detach_policy.call_count == 2
    
    def test_detach_policy_from_all_targets_partial_failure(self, scp_manager):
        """Test policy detachment with partial failures (should continue)."""
        mock_response = {
            'Targets': [
                {'TargetId': 'ou-12345'},
                {'TargetId': 'ou-67890'}
            ]
        }
        
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [mock_response]
        scp_manager.organizations_client.get_paginator.return_value = mock_paginator
        
        # First detach succeeds, second fails
        scp_manager.organizations_client.detach_policy.side_effect = [
            {},
            ClientError({'Error': {'Code': 'PolicyNotAttachedException', 'Message': 'Not attached'}}, 'DetachPolicy')
        ]
        
        # Should not raise exception, just continue
        scp_manager._detach_policy_from_all_targets('policy-1')
        
        assert scp_manager.organizations_client.detach_policy.call_count == 2
