"""AWS Control Tower landing zone deployment automation.

This module provides the ControlTowerDeployer class for managing Control Tower
landing zone deployment using the CreateLandingZone API, monitoring deployment
status, and handling errors with proper rollback guidance.
"""

import json
import time
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

from src.core.aws_client import AWSClientManager


class ControlTowerError(Exception):
    """Base exception for Control Tower operations."""
    pass


class DeploymentError(ControlTowerError):
    """Raised when Control Tower deployment fails."""
    pass


class ControlTowerDeployer:
    """Manages AWS Control Tower landing zone deployment.
    
    This class handles Control Tower deployment using the CreateLandingZone API,
    monitors deployment status, and provides error handling and rollback guidance.
    """
    
    # Default landing zone version (current latest)
    DEFAULT_LANDING_ZONE_VERSION = "3.3"
    
    # Deployment timeout in seconds (90 minutes)
    DEFAULT_TIMEOUT_SECONDS = 5400
    
    # Status polling interval in seconds
    POLLING_INTERVAL_SECONDS = 30
    
    def __init__(self, aws_client_manager: AWSClientManager) -> None:
        """Initialize the Control Tower deployer.
        
        Args:
            aws_client_manager: AWS client manager instance
        """
        self.aws_client_manager = aws_client_manager
        self._control_tower_client = None
        
    def _get_client(self):
        """Get Control Tower client.
        
        Returns:
            Control Tower boto3 client
        """
        return self.aws_client_manager.get_client('controltower')
        self._control_tower_client = None
    
    @property
    def control_tower_client(self):
        """Get Control Tower client with lazy initialization."""
        if self._control_tower_client is None:
            self._control_tower_client = self.aws_client_manager.get_client('controltower')
        return self._control_tower_client
    
    def create_landing_zone(self, manifest: Dict[str, Any], 
                          version: Optional[str] = None,
                          tags: Optional[Dict[str, str]] = None) -> str:
        """Create Control Tower landing zone from manifest.
        
        Args:
            manifest: Landing zone manifest dictionary
            version: Control Tower landing zone version (default: 3.3)
            tags: Optional tags for the landing zone
            
        Returns:
            Landing zone operation ID for status monitoring
            
        Raises:
            DeploymentError: When deployment fails
            ControlTowerError: When manifest is invalid or other errors occur
        """
        if version is None:
            version = self.DEFAULT_LANDING_ZONE_VERSION
        
        try:
            # Validate manifest before deployment
            self._validate_manifest(manifest)
            
            # Prepare API parameters
            params = {
                'manifest': manifest,
                'version': version
            }
            
            if tags:
                params['tags'] = tags
            
            # Create landing zone
            response = self.control_tower_client.create_landing_zone(**params)
            
            operation_id = response['operationIdentifier']
            landing_zone_arn = response['arn']
            
            print(f"✓ Landing zone creation initiated")
            print(f"  Operation ID: {operation_id}")
            print(f"  Landing Zone ARN: {landing_zone_arn}")
            
            return operation_id
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ValidationException':
                raise ControlTowerError(f"Invalid manifest or parameters: {error_message}")
            elif error_code == 'ConflictException':
                raise DeploymentError(f"Landing zone already exists or conflicting operation: {error_message}")
            elif error_code == 'AccessDeniedException':
                raise DeploymentError(f"Insufficient permissions: {error_message}")
            elif error_code == 'ServiceQuotaExceededException':
                raise DeploymentError(f"AWS service limits exceeded: {error_message}")
            elif error_code == 'ThrottlingException':
                raise DeploymentError(f"API rate limit exceeded: {error_message}")
            else:
                raise DeploymentError(f"Control Tower deployment failed: {error_message}")
    
    def get_landing_zone_status(self, operation_id: str) -> Dict[str, Any]:
        """Get landing zone operation status.
        
        Args:
            operation_id: Landing zone operation identifier
            
        Returns:
            Dictionary containing operation status and details
            
        Raises:
            ControlTowerError: When status check fails
        """
        try:
            response = self.control_tower_client.get_landing_zone_operation(
                operationIdentifier=operation_id
            )
            
            operation_detail = response['operationDetails']
            
            return {
                'status': operation_detail.get('status'),
                'operation_type': operation_detail.get('operationType'),
                'start_time': operation_detail.get('startTime'),
                'end_time': operation_detail.get('endTime'),
                'status_message': operation_detail.get('statusMessage')
            }
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            raise ControlTowerError(f"Failed to get operation status: {error_message}")
    
    def wait_for_deployment_completion(self, operation_id: str,
                                     timeout_seconds: Optional[int] = None) -> bool:
        """Wait for deployment completion with timeout handling.
        
        Args:
            operation_id: Landing zone operation identifier
            timeout_seconds: Maximum wait time (default: 90 minutes)
            
        Returns:
            True if deployment succeeded, False if failed
            
        Raises:
            DeploymentError: When deployment times out or fails
        """
        if timeout_seconds is None:
            timeout_seconds = self.DEFAULT_TIMEOUT_SECONDS
        
        start_time = time.time()
        
        print(f"⏳ Monitoring deployment progress (timeout: {timeout_seconds//60} minutes)...")
        
        while True:
            try:
                status_info = self.get_landing_zone_status(operation_id)
                status = status_info['status']
                
                elapsed_time = int(time.time() - start_time)
                elapsed_minutes = elapsed_time // 60
                
                if status == 'SUCCEEDED':
                    print(f"✅ Landing zone deployment completed successfully ({elapsed_minutes} minutes)")
                    return True
                elif status == 'FAILED':
                    error_msg = status_info.get('status_message', 'Unknown error')
                    print(f"❌ Landing zone deployment failed: {error_msg}")
                    raise DeploymentError(f"Deployment failed: {error_msg}")
                elif status == 'IN_PROGRESS':
                    print(f"⏳ Deployment in progress... ({elapsed_minutes} minutes elapsed)")
                else:
                    print(f"⚠️  Unknown status: {status}")
                
                # Check timeout
                if elapsed_time >= timeout_seconds:
                    raise DeploymentError(
                        f"Deployment timeout after {timeout_seconds//60} minutes. "
                        f"Operation ID: {operation_id}"
                    )
                
                # Wait before next check
                time.sleep(self.POLLING_INTERVAL_SECONDS)
                
            except KeyboardInterrupt:
                print(f"\n⚠️  Deployment monitoring interrupted by user")
                print(f"   Operation ID: {operation_id}")
                print(f"   Use this ID to check status later")
                raise DeploymentError("Deployment monitoring interrupted")
    
    def get_landing_zone_details(self, landing_zone_arn: str) -> Dict[str, Any]:
        """Get detailed information about a landing zone.
        
        Args:
            landing_zone_arn: Landing zone ARN
            
        Returns:
            Dictionary containing landing zone details
            
        Raises:
            ControlTowerError: When retrieval fails
        """
        try:
            response = self.control_tower_client.get_landing_zone(
                landingZoneIdentifier=landing_zone_arn
            )
            
            landing_zone = response['landingZone']
            
            return {
                'arn': landing_zone.get('arn'),
                'status': landing_zone.get('status'),
                'latest_available_version': landing_zone.get('latestAvailableVersion'),
                'version': landing_zone.get('version'),
                'manifest': landing_zone.get('manifest'),
                'drift_status': landing_zone.get('driftStatus')
            }
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            raise ControlTowerError(f"Failed to get landing zone details: {error_message}")
    
    def _validate_manifest(self, manifest: Dict[str, Any]) -> None:
        """Validate manifest structure before deployment.
        
        Args:
            manifest: Landing zone manifest dictionary
            
        Raises:
            ControlTowerError: When manifest validation fails
        """
        required_fields = ['governedRegions', 'organizationStructure', 'centralizedLogging', 'securityRoles']
        
        for field in required_fields:
            if field not in manifest:
                raise ControlTowerError(f"Missing required field in manifest: {field}")
        
        # Validate governed regions
        if not isinstance(manifest['governedRegions'], list) or not manifest['governedRegions']:
            raise ControlTowerError("governedRegions must be a non-empty list")
        
        # Validate organization structure
        org_structure = manifest['organizationStructure']
        if 'security' not in org_structure:
            raise ControlTowerError("organizationStructure must contain 'security' OU")
        
        # Validate centralized logging
        centralized_logging = manifest['centralizedLogging']
        if 'accountId' not in centralized_logging:
            raise ControlTowerError("centralizedLogging must contain 'accountId'")
        
        # Validate security roles
        security_roles = manifest['securityRoles']
        if 'accountId' not in security_roles:
            raise ControlTowerError("securityRoles must contain 'accountId'")
        
        # Ensure different account IDs for logging and security
        log_account = centralized_logging['accountId']
        security_account = security_roles['accountId']
        
        if log_account == security_account:
            raise ControlTowerError(
                "centralizedLogging and securityRoles must use different account IDs"
            )
    
    def extract_audit_account_from_manifest(self, manifest: Dict[str, Any]) -> Optional[str]:
        """Extract audit account ID from landing zone manifest.
        
        Args:
            manifest: Landing zone manifest dictionary
            
        Returns:
            Audit account ID if found, None otherwise
        """
        try:
            # Audit account is stored in securityRoles section
            security_roles = manifest.get('securityRoles', {})
            audit_account_id = security_roles.get('accountId')
            
            if audit_account_id and len(audit_account_id) == 12 and audit_account_id.isdigit():
                return audit_account_id
            
            return None
            
        except Exception:
            return None
    
    def get_landing_zone_details(self, landing_zone_arn: str) -> Dict[str, Any]:
        """Get landing zone details using Control Tower API.
        
        Args:
            landing_zone_arn: Landing zone ARN
            
        Returns:
            Landing zone details dictionary
            
        Raises:
            ControlTowerError: When API call fails
        """
        try:
            client = self._get_client()
            
            # Extract landing zone identifier from ARN
            landing_zone_id = landing_zone_arn.split('/')[-1]
            
            response = client.get_landing_zone(landingZoneIdentifier=landing_zone_id)
            landing_zone = response['landingZone']
            
            # Transform response to match test expectations
            return {
                'arn': landing_zone['arn'],
                'status': landing_zone['status'],
                'latest_available_version': landing_zone['latestAvailableVersion'],
                'version': landing_zone['version'],
                'manifest': landing_zone['manifest'],
                'drift_status': landing_zone['driftStatus']
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise ControlTowerError(f"Failed to get landing zone details: Landing zone not found")
            elif error_code == 'AccessDeniedException':
                raise ControlTowerError("Failed to get landing zone details: Insufficient permissions")
            else:
                raise ControlTowerError(f"Failed to get landing zone details: {e}")
        except Exception as e:
            raise ControlTowerError(f"Unexpected error getting landing zone details: {e}")
    
    def get_audit_account_id_from_landing_zone(self, landing_zone_arn: str) -> Optional[str]:
        """Get audit account ID from deployed landing zone.
        
        Args:
            landing_zone_arn: Landing zone ARN
            
        Returns:
            Audit account ID if found, None otherwise
        """
        try:
            landing_zone_details = self.get_landing_zone_details(landing_zone_arn)
            manifest = landing_zone_details.get('manifest', {})
            
            return self.extract_audit_account_from_manifest(manifest)
            
        except ControlTowerError:
            return None
