"""Safety and confirmation system for AWS Control Tower automation.

This module provides multiple confirmation layers for destructive operations,
countdown mechanisms, and audit logging to prevent accidental deployments.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ConfirmationRequest:
    """Request for user confirmation."""

    operation: str
    description: str
    impact_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    configuration_summary: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None


class SafetyManager:
    """Safety and confirmation manager for high-impact operations.

    This class provides multiple layers of confirmation for operations
    that could have significant impact on AWS environments.
    """

    def __init__(self, enable_confirmations: bool = True) -> None:
        """Initialize safety manager.

        Args:
            enable_confirmations: Whether to enable confirmation prompts
                                 (can be disabled for automated testing)
        """
        self.enable_confirmations = enable_confirmations
        self.audit_log: List[Dict[str, Any]] = []

    def request_confirmation(self, request: ConfirmationRequest) -> bool:
        """Request user confirmation for an operation.

        Args:
            request: ConfirmationRequest with operation details

        Returns:
            True if user confirms, False otherwise
        """
        if not self.enable_confirmations:
            self._log_confirmation(
                request, True, "Auto-confirmed (testing mode)"
            )
            return True

        print("\n" + "=" * 60)
        print("CONFIRMATION REQUIRED")
        print("=" * 60)
        print(f"Operation: {request.operation}")
        print(f"Impact Level: {request.impact_level}")
        print(f"Description: {request.description}")

        # Display warnings if any
        if request.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in request.warnings:
                print(f"   • {warning}")

        # Display configuration summary
        if request.configuration_summary:
            print("\nConfiguration Summary:")
            self._display_configuration(request.configuration_summary)

        # Get user confirmation
        confirmed = self._get_user_confirmation(request.impact_level)

        # Log the confirmation
        self._log_confirmation(
            request,
            confirmed,
            "User confirmed" if confirmed else "User declined",
        )

        return confirmed

    def _display_configuration(
        self, config: Dict[str, Any], indent: int = 0
    ) -> None:
        """Display configuration in a readable format.

        Args:
            config: Configuration dictionary to display
            indent: Indentation level for nested items
        """
        prefix = "  " * indent

        for key, value in config.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                self._display_configuration(value, indent + 1)
            elif isinstance(value, list):
                print(f"{prefix}{key}: {', '.join(map(str, value))}")
            else:
                print(f"{prefix}{key}: {value}")

    def _get_user_confirmation(self, impact_level: str) -> bool:
        """Get confirmation from user with appropriate safeguards.

        Args:
            impact_level: Impact level of the operation

        Returns:
            True if user confirms, False otherwise
        """
        # Determine confirmation requirements based on impact level
        if impact_level == "CRITICAL":
            return self._get_critical_confirmation()
        elif impact_level == "HIGH":
            return self._get_high_confirmation()
        else:
            return self._get_standard_confirmation()

    def _get_standard_confirmation(self) -> bool:
        """Get standard confirmation (y/n).

        Returns:
            True if user confirms, False otherwise
        """
        print("\nDo you want to proceed? (y/n): ", end="")
        response = input().strip().lower()
        return response in ["y", "yes"]

    def _get_high_confirmation(self) -> bool:
        """Get high-impact confirmation with countdown.

        Returns:
            True if user confirms, False otherwise
        """
        print("\n⚠️  HIGH IMPACT OPERATION")
        print(
            "This operation will make significant changes to your AWS environment."
        )

        # First confirmation
        print("\nType 'CONFIRM' to proceed: ", end="")
        response = input().strip()

        if response != "CONFIRM":
            print("Operation cancelled.")
            return False

        # Countdown with cancel option
        return self._countdown_confirmation(5)

    def _get_critical_confirmation(self) -> bool:
        """Get critical confirmation with multiple steps.

        Returns:
            True if user confirms, False otherwise
        """
        print("\n🚨 CRITICAL OPERATION")
        print(
            "This operation will make irreversible changes to your AWS environment."
        )
        print("Please review all details carefully before proceeding.")

        # First confirmation - understanding
        print(
            "\nDo you understand the impact of this operation? (yes/no): ",
            end="",
        )
        response = input().strip().lower()

        if response not in ["yes"]:
            print("Operation cancelled. Please review the operation details.")
            return False

        # Second confirmation - explicit consent
        print("\nType 'I UNDERSTAND THE RISKS' to continue: ", end="")
        response = input().strip()

        if response != "I UNDERSTAND THE RISKS":
            print("Operation cancelled.")
            return False

        # Final countdown
        return self._countdown_confirmation(10)

    def _countdown_confirmation(self, seconds: int) -> bool:
        """Display countdown with cancel option.

        Args:
            seconds: Number of seconds to count down

        Returns:
            True if countdown completes, False if cancelled
        """
        print(f"\nStarting in {seconds} seconds... (Press Ctrl+C to cancel)")

        try:
            for i in range(seconds, 0, -1):
                print(f"\rProceeding in {i} seconds...", end="", flush=True)
                time.sleep(1)

            print("\rProceeding now...                    ")
            return True

        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            return False

    def _log_confirmation(
        self, request: ConfirmationRequest, confirmed: bool, reason: str
    ) -> None:
        """Log confirmation request and result.

        Args:
            request: The confirmation request
            confirmed: Whether the operation was confirmed
            reason: Reason for the confirmation result
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": request.operation,
            "impact_level": request.impact_level,
            "confirmed": confirmed,
            "reason": reason,
            "description": request.description,
        }

        if request.configuration_summary:
            log_entry["configuration"] = request.configuration_summary

        self.audit_log.append(log_entry)

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get complete audit log of confirmations.

        Returns:
            List of audit log entries
        """
        return self.audit_log.copy()

    def display_configuration_review(self, config: Dict[str, Any]) -> None:
        """Display configuration for review before deployment.

        Args:
            config: Configuration dictionary to review
        """
        print("\n" + "=" * 60)
        print("CONFIGURATION REVIEW")
        print("=" * 60)
        print("Please review the following configuration:")
        print()

        self._display_configuration(config)

        print("\n" + "=" * 60)

    def create_deployment_confirmation(
        self, config: Dict[str, Any]
    ) -> ConfirmationRequest:
        """Create confirmation request for Control Tower deployment.

        Args:
            config: Deployment configuration

        Returns:
            ConfirmationRequest for the deployment
        """
        warnings = []

        # Add warnings based on configuration
        if config.get("scp_tier") == "strict":
            warnings.append(
                "Strict SCP tier will apply maximum security restrictions"
            )

        if config.get("aws", {}).get("region_deny_enabled"):
            warnings.append(
                "Region deny policy will restrict access to non-governed regions"
            )

        return ConfirmationRequest(
            operation="Deploy AWS Control Tower Landing Zone",
            description=(
                "This will deploy AWS Control Tower with the specified configuration. "
                "This operation creates shared accounts, organizational units, "
                "and applies governance controls across your organization."
            ),
            impact_level="CRITICAL",
            configuration_summary=config,
            warnings=warnings if warnings else None,
        )
    
    def confirm_security_baseline_deployment(self) -> bool:
        """Confirm security baseline deployment with appropriate safeguards.
        
        Returns:
            True if user confirms deployment, False otherwise
        """
        request = ConfirmationRequest(
            operation="Deploy Security Baseline",
            description=(
                "This will deploy organization-wide security baseline including "
                "AWS Config aggregator, GuardDuty with delegated administration, "
                "and Security Hub with foundational standards."
            ),
            impact_level="HIGH",
            warnings=[
                "Security services will be enabled across all organization accounts",
                "Delegated administrator will be configured for security services",
                "Security standards and compliance monitoring will be activated"
            ]
        )
        
        return self.request_confirmation(request)
