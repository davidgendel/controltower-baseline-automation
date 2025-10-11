"""Post-deployment orchestration for security services coordination.

This module orchestrates the complete post-deployment security baseline setup,
managing dependencies between Config, GuardDuty, and Security Hub services.
"""

from typing import Dict, List, Optional, Any
import logging
import time

from ..core.aws_client import AWSClientManager
from ..core.config import Configuration
from .aws_config import ConfigOrganizationManager
from .guardduty import GuardDutyOrganizationManager
from .security_hub import SecurityHubOrganizationManager


logger = logging.getLogger(__name__)


class PostDeploymentOrchestrationError(Exception):
    """Raised when post-deployment orchestration fails."""
    pass


class PostDeploymentOrchestrator:
    """Orchestrates complete post-deployment security services setup."""
    
    def __init__(self, config: Configuration, aws_client: AWSClientManager):
        """Initialize post-deployment orchestrator.
        
        Args:
            config: Configuration instance
            aws_client: AWS client manager instance
        """
        self.config = config
        self.aws_client = aws_client
        self.config_manager = ConfigOrganizationManager(config, aws_client)
        self.guardduty_manager = GuardDutyOrganizationManager(config, aws_client)
        self.security_hub_manager = SecurityHubOrganizationManager(config, aws_client)
        
    def orchestrate_security_baseline(self, audit_account_id: str) -> Dict[str, Any]:
        """Orchestrate complete security baseline deployment.
        
        Args:
            audit_account_id: Account ID to use as delegated administrator
            
        Returns:
            Dict containing deployment results for all services
            
        Raises:
            PostDeploymentOrchestrationError: When orchestration fails
        """
        results = {
            'config': {'status': 'pending', 'details': {}},
            'guardduty': {'status': 'pending', 'details': {}},
            'security_hub': {'status': 'pending', 'details': {}},
            'overall_status': 'in_progress'
        }
        
        try:
            logger.info("Starting security baseline orchestration")
            
            # Step 1: Configure AWS Config (prerequisite for Security Hub)
            logger.info("Configuring AWS Config organization setup")
            self.config_manager.enable_delegated_administrator(audit_account_id)
            config_aggregator = self.config_manager.create_organization_aggregator()
            results['config'] = {
                'status': 'success',
                'details': {'aggregator': config_aggregator}
            }
            
            # Step 2: Configure GuardDuty
            logger.info("Configuring GuardDuty organization setup")
            self.guardduty_manager.enable_delegated_administrator(audit_account_id)
            guardduty_config = self.guardduty_manager.enable_organization_guardduty()
            self.guardduty_manager.set_finding_frequency('SIX_HOURS')
            results['guardduty'] = {
                'status': 'success',
                'details': guardduty_config
            }
            
            # Step 3: Configure Security Hub (depends on Config)
            logger.info("Configuring Security Hub organization setup")
            self.security_hub_manager.enable_delegated_administrator(audit_account_id)
            security_hub_config = self.security_hub_manager.enable_organization_security_hub()
            standards = self.security_hub_manager.enable_foundational_standards()
            results['security_hub'] = {
                'status': 'success',
                'details': {**security_hub_config, 'standards': standards}
            }
            
            results['overall_status'] = 'success'
            logger.info("Security baseline orchestration completed successfully")
            
        except Exception as e:
            results['overall_status'] = 'failed'
            results['error'] = str(e)
            logger.error(f"Security baseline orchestration failed: {e}")
            raise PostDeploymentOrchestrationError(f"Orchestration failed: {e}")
        
        return results
    
    def validate_service_health(self) -> Dict[str, Dict[str, bool]]:
        """Validate health status of all security services.
        
        Returns:
            Dict containing health status for each service
        """
        logger.info("Validating security services health")
        
        health_status = {
            'config': self.config_manager.validate_config_setup(),
            'guardduty': self.guardduty_manager.validate_guardduty_setup(),
            'security_hub': self.security_hub_manager.validate_security_hub_setup()
        }
        
        # Calculate overall health
        all_healthy = True
        for service, status in health_status.items():
            service_healthy = all(status.values())
            health_status[service]['overall_healthy'] = service_healthy
            if not service_healthy:
                all_healthy = False
        
        health_status['overall_healthy'] = all_healthy
        
        return health_status
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status for all security services.
        
        Returns:
            Dict containing deployment status and service details
        """
        status = {
            'timestamp': time.time(),
            'services': {},
            'summary': {
                'total_services': 3,
                'healthy_services': 0,
                'failed_services': 0
            }
        }
        
        health_check = self.validate_service_health()
        
        for service in ['config', 'guardduty', 'security_hub']:
            service_status = health_check.get(service, {})
            is_healthy = service_status.get('overall_healthy', False)
            
            status['services'][service] = {
                'healthy': is_healthy,
                'details': service_status
            }
            
            if is_healthy:
                status['summary']['healthy_services'] += 1
            else:
                status['summary']['failed_services'] += 1
        
        status['summary']['deployment_complete'] = (
            status['summary']['healthy_services'] == status['summary']['total_services']
        )
        
        return status
