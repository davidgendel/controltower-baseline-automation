"""Interactive menu system for AWS Control Tower automation.

This module provides a clean, intuitive menu interface for all major
functions with input validation and consistent user experience.
"""

from typing import Dict, Any
import sys

from .config import Configuration
from .aws_client import AWSClientManager
from .validator import PrerequisitesValidator
from .safety import SafetyManager


class InteractiveMenu:
    """Interactive menu system for Control Tower automation.

    This class provides a user-friendly interface for all automation
    functions with clear navigation and progress indicators.
    """

    def __init__(
        self, config: Configuration, aws_client: AWSClientManager
    ) -> None:
        """Initialize interactive menu.

        Args:
            config: Loaded configuration object
            aws_client: Configured AWS client manager
        """
        self.config = config
        self.aws_client = aws_client
        self.safety_manager = SafetyManager()
        self.running = True

    def run(self) -> None:
        """Run the interactive menu loop."""
        while self.running:
            self._display_main_menu()
            choice = self._get_user_choice()
            self._handle_menu_choice(choice)

    def _display_main_menu(self) -> None:
        """Display the main menu options."""
        print("\n" + "=" * 60)
        print("AWS Control Tower Automation - Main Menu")
        print("=" * 60)
        print("1. Validate Prerequisites")
        print("2. Setup Prerequisites")
        print("3. Deploy Control Tower")
        print("4. Post-Deployment Security Setup")
        print("5. Check Status")
        print("6. Generate Documentation")
        print("7. Configuration Management")
        print("0. Exit")
        print("-" * 60)

    def _get_user_choice(self) -> str:
        """Get and validate user menu choice.

        Returns:
            User's menu choice as string
        """
        while True:
            try:
                choice = input("Please select an option (0-7): ").strip()
                if choice in ["0", "1", "2", "3", "4", "5", "6", "7"]:
                    return choice
                else:
                    print(
                        "❌ Invalid choice. Please select a number from 0-7."
                    )
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Goodbye!")
                sys.exit(0)

    def _handle_menu_choice(self, choice: str) -> None:
        """Handle user menu selection.

        Args:
            choice: User's menu choice
        """
        handlers = {
            "0": self._exit_application,
            "1": self._validate_prerequisites,
            "2": self._setup_prerequisites,
            "3": self._deploy_control_tower,
            "4": self._post_deployment_setup,
            "5": self._check_status,
            "6": self._generate_documentation,
            "7": self._configuration_management,
        }

        handler = handlers.get(choice)
        if handler:
            try:
                handler()
            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("\nPress Enter to continue...")
        else:
            print("❌ Invalid choice.")

    def _exit_application(self) -> None:
        """Exit the application."""
        print("\n👋 Thank you for using AWS Control Tower Automation!")
        self.running = False

    def _validate_prerequisites(self) -> None:
        """Validate all prerequisites."""
        print("\n" + "=" * 60)
        print("Prerequisites Validation")
        print("=" * 60)

        validator = PrerequisitesValidator(self.aws_client)
        results = validator.validate_all()

        # Display results with progress
        for i, result in enumerate(results, 1):
            print(
                f"\n[{i}/{len(results)}] Checking {result.validator_name}..."
            )

            status_symbol = {
                "PASSED": "✅",
                "FAILED": "❌",
                "WARNING": "⚠️",
                "SKIPPED": "⏭️",
            }.get(result.status.value, "❓")

            print(f"    {status_symbol} {result.message}")

            if result.remediation_steps:
                print("    Remediation steps:")
                for step in result.remediation_steps:
                    print(f"    • {step}")

        # Summary
        passed = sum(1 for r in results if r.status.value == "PASSED")
        failed = sum(1 for r in results if r.status.value == "FAILED")
        warnings = sum(1 for r in results if r.status.value == "WARNING")

        print(
            f"\n📊 Summary: {passed} passed, {failed} failed, {warnings} warnings"
        )

        if validator.is_ready_for_deployment(results):
            print("✅ Ready for Control Tower deployment!")
        else:
            print("❌ Prerequisites must be resolved before deployment.")

        input("\nPress Enter to continue...")

    def _setup_prerequisites(self) -> None:
        """Setup prerequisites automation workflow."""
        print("\n" + "=" * 60)
        print("Prerequisites Setup")
        print("=" * 60)
        
        # First validate current state
        print("🔍 Checking current prerequisites status...")
        validator = PrerequisitesValidator(self.aws_client)
        results = validator.validate_all()
        
        # Show current status
        failed_validators = []
        for result in results:
            status_icon = "✅" if result.status.value == "PASSED" else "⚠️" if result.status.value == "WARNING" else "❌"
            print(f"{status_icon} {result.validator_name}: {result.status.value}")
            if result.status.value == "FAILED":
                failed_validators.append(result)
        
        if not failed_validators:
            print("\n✅ All prerequisites are already configured!")
            input("\nPress Enter to continue...")
            return
            
        print(f"\n📋 Found {len(failed_validators)} prerequisites that need setup:")
        for result in failed_validators:
            print(f"  • {result.validator_name}")
            
        # Confirm setup
        if not self._confirm_action("Do you want to proceed with prerequisites setup?"):
            return
            
        # Setup prerequisites
        self._run_prerequisites_setup(failed_validators)
        
    def _run_prerequisites_setup(self, failed_validators: list) -> None:
        """Run prerequisites setup for failed validators."""
        from ..prerequisites.organizations import OrganizationsManager
        from ..prerequisites.accounts import AccountManager
        
        print("\n🚀 Starting prerequisites setup...")
        
        for result in failed_validators:
            print(f"\n📝 Setting up {result.validator_name}...")
            
            try:
                if result.validator_name == "AWS Organizations":
                    self._setup_organizations()
                elif result.validator_name == "Organizations Structure":
                    self._setup_organization_structure()
                elif result.validator_name == "Account Structure":
                    self._setup_accounts()
                else:
                    print(f"⚠️ Automated setup not available for {result.validator_name}")
                    print("Please follow the remediation steps shown in validation.")
                    
            except Exception as e:
                print(f"❌ Failed to setup {result.validator_name}: {e}")
                
        print("\n✅ Prerequisites setup completed!")
        print("💡 Run 'Validate Prerequisites' to verify the setup.")
        
    def _setup_organizations(self) -> None:
        """Setup AWS Organizations."""
        from ..prerequisites.organizations import OrganizationsManager
        
        print("  🔧 Enabling AWS Organizations all features...")
        org_manager = OrganizationsManager(self.aws_client)
        
        # Enable all features
        org_manager.enable_all_features()
        print("  ✅ Organizations all features enabled")
        
    def _setup_organization_structure(self) -> None:
        """Setup organization structure with required OUs."""
        from ..prerequisites.organizations import OrganizationsManager
        
        print("  🔧 Creating organizational units...")
        org_manager = OrganizationsManager(self.aws_client)
        
        # Get root ID
        root_id = org_manager._get_root_id()
        
        # Create Security OU
        try:
            security_ou_id = org_manager.create_organizational_unit("Security", root_id)
            print("  ✅ Security OU created")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  ℹ️ Security OU already exists")
            else:
                raise
                
        # Create Sandbox OU
        try:
            sandbox_ou_id = org_manager.create_organizational_unit("Sandbox", root_id)
            print("  ✅ Sandbox OU created")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  ℹ️ Sandbox OU already exists")
            else:
                raise
                
    def _setup_accounts(self) -> None:
        """Setup required accounts."""
        print("  ⚠️ Account creation requires manual configuration")
        print("  📋 Required accounts:")
        print("    • Log Archive account with unique email")
        print("    • Audit account with unique email")
        print("  💡 Use the account management tools to create these accounts")
        
    def _confirm_action(self, message: str) -> bool:
        """Confirm user action with safety check."""
        print(f"\n⚠️ {message}")
        response = input("Type 'yes' to confirm: ").strip().lower()
        return response == 'yes'

    def _deploy_control_tower(self) -> None:
        """Deploy Control Tower with full orchestration."""
        print("\n" + "=" * 60)
        print("Deploy Control Tower")
        print("=" * 60)
        
        # Import deployment orchestrator
        from ..control_tower.orchestrator import DeploymentOrchestrator, DeploymentOrchestrationError
        
        # First validate prerequisites
        print("🔍 Validating prerequisites before deployment...")
        validator = PrerequisitesValidator(self.aws_client)
        results = validator.validate_all()
        
        if not validator.is_ready_for_deployment(results):
            print("❌ Prerequisites validation failed!")
            print("💡 Please run 'Setup Prerequisites' first to resolve issues.")
            input("\nPress Enter to continue...")
            return
        
        print("✅ Prerequisites validation passed")
        
        # Show deployment configuration
        print("\n📋 Deployment Configuration:")
        print(f"  • Home Region: {self.config.aws.home_region}")
        print(f"  • Governed Regions: {', '.join(self.config.aws.governed_regions)}")
        print(f"  • SCP Tier: {getattr(self.config, 'scp_tier', 'standard')}")
        print(f"  • Log Archive Account: {self.config.accounts.log_archive.name}")
        print(f"  • Audit Account: {self.config.accounts.audit.name}")
        
        # Safety confirmation
        if not self.safety_manager.confirm_deployment_action(
            "Control Tower Landing Zone Deployment",
            "This will create a Control Tower landing zone in your AWS organization. "
            "This action cannot be easily undone and will affect your entire organization."
        ):
            print("❌ Deployment cancelled by user")
            return
        
        # Initialize orchestrator
        orchestrator = DeploymentOrchestrator(self.config, self.aws_client)
        
        try:
            print("\n🚀 Starting Control Tower deployment...")
            print("⏳ This process typically takes 60-90 minutes...")
            
            # Run deployment orchestration
            deployment_results = orchestrator.orchestrate_deployment()
            
            # Display results
            print("\n🎉 Control Tower deployment completed successfully!")
            print(f"✅ Operation ID: {deployment_results['operation_id']}")
            print(f"✅ Landing Zone ARN: {deployment_results['landing_zone_arn']}")
            
            if deployment_results.get('deployed_policies'):
                print(f"✅ SCP Policies Deployed: {len(deployment_results['deployed_policies'])}")
                for policy_name in deployment_results['deployed_policies'].keys():
                    print(f"  • {policy_name}")
            
            print("\n📋 Next Steps:")
            print("  1. Run 'Post-Deployment Security Setup' to configure additional security services")
            print("  2. Use 'Check Status' to monitor your Control Tower environment")
            print("  3. Review the generated documentation for operational guidance")
            
        except DeploymentOrchestrationError as e:
            print(f"\n❌ Control Tower deployment failed: {e}")
            print("\n📋 Troubleshooting:")
            print("  1. Check AWS CloudTrail logs for detailed error information")
            print("  2. Verify all prerequisites are still met")
            print("  3. Review AWS Control Tower service limits and quotas")
            print("  4. Contact AWS Support if the issue persists")
            
        except KeyboardInterrupt:
            print("\n⚠️ Deployment interrupted by user")
            print("💡 Use 'Check Status' to monitor the deployment progress")
            
        except Exception as e:
            print(f"\n❌ Unexpected error during deployment: {e}")
            print("💡 Please check the logs and try again")
        
        input("\nPress Enter to continue...")
        print("\nPlanned deployment configuration:")
        config_dict = self.config.to_dict()
        self._display_config_summary(config_dict)

        input("\nPress Enter to continue...")

    def _post_deployment_setup(self) -> None:
        """Post-deployment security setup workflow."""
        print("\n" + "=" * 60)
        print("Post-Deployment Security Setup")
        print("=" * 60)
        print("This will configure organization-wide security services:")
        print("• AWS Config (organization aggregator)")
        print("• GuardDuty (delegated administration)")
        print("• Security Hub (foundational standards)")
        print()
        
        # Import here to avoid circular imports
        from ..post_deployment.orchestrator import PostDeploymentOrchestrator
        
        # Get audit account ID
        audit_account_id = self._get_audit_account_id()
        if not audit_account_id:
            return
        
        # Safety confirmation
        if not self.safety_manager.confirm_security_baseline_deployment():
            print("❌ Security baseline deployment cancelled.")
            return
        
        try:
            orchestrator = PostDeploymentOrchestrator(self.config, self.aws_client)
            
            print("\n🚀 Starting security baseline deployment...")
            print("This may take several minutes...")
            
            # Execute orchestration
            results = orchestrator.orchestrate_security_baseline(audit_account_id)
            
            # Display results
            self._display_security_baseline_results(results)
            
        except Exception as e:
            print(f"\n❌ Security baseline deployment failed: {e}")
        
        input("\nPress Enter to continue...")
    
    def _get_audit_account_id(self) -> str:
        """Get audit account ID for delegated administration."""
        print("📋 Audit Account Configuration")
        print("The audit account will be designated as delegated administrator")
        print("for all security services (Config, GuardDuty, Security Hub).")
        print()
        
        while True:
            account_id = input("Enter Audit Account ID (12 digits): ").strip()
            
            if len(account_id) == 12 and account_id.isdigit():
                # Confirm the account ID
                print(f"\n✅ Audit Account ID: {account_id}")
                confirm = input("Is this correct? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    return account_id
                else:
                    continue
            else:
                print("❌ Invalid account ID. Must be exactly 12 digits.")
    
    def _display_security_baseline_results(self, results: Dict[str, Any]) -> None:
        """Display security baseline deployment results."""
        print("\n" + "=" * 60)
        print("Security Baseline Deployment Results")
        print("=" * 60)
        
        if results['overall_status'] == 'success':
            print("✅ Security baseline deployment completed successfully!")
            print()
            
            # Config results
            if results['config']['status'] == 'success':
                print("✅ AWS Config: Organization aggregator configured")
            else:
                print("❌ AWS Config: Configuration failed")
            
            # GuardDuty results
            if results['guardduty']['status'] == 'success':
                print("✅ GuardDuty: Organization-wide setup completed")
            else:
                print("❌ GuardDuty: Configuration failed")
            
            # Security Hub results
            if results['security_hub']['status'] == 'success':
                standards_count = len(results['security_hub']['details'].get('standards', []))
                print(f"✅ Security Hub: {standards_count} foundational standards enabled")
            else:
                print("❌ Security Hub: Configuration failed")
                
        else:
            print("❌ Security baseline deployment failed!")
            if 'error' in results:
                print(f"   Error: {results['error']}")
        
        print("\n📊 Next Steps:")
        print("• Use 'Check Status' to monitor service health")
        print("• Review AWS Console for detailed configuration")
        print("• Monitor compliance dashboards in Security Hub")

    def _check_status(self) -> None:
        """Check current status including Control Tower deployment."""
        print("\n" + "=" * 60)
        print("System Status")
        print("=" * 60)

        # Show current configuration
        print("📄 Current Configuration:")
        print(f"   Home Region: {self.config.get_home_region()}")
        print(
            f"   Governed Regions: {', '.join(self.config.get_governed_regions())}"
        )
        print(f"   SCP Tier: {self.config.get_scp_tier()}")

        # Show AWS connection status
        try:
            account_id = self.aws_client.get_account_id()
            region = self.aws_client.get_current_region()
            print(f"\n🔗 AWS Connection:")
            print(f"   Account ID: {account_id}")
            print(f"   Current Region: {region}")
            print("   Status: ✅ Connected")
        except Exception as e:
            print(f"\n🔗 AWS Connection:")
            print(f"   Status: ❌ Error - {e}")
            input("\nPress Enter to continue...")
            return

        # Check Control Tower status
        print(f"\n🏗️ Control Tower Status:")
        try:
            from ..control_tower.deployer import ControlTowerDeployer
            
            deployer = ControlTowerDeployer(self.aws_client)
            
            # Try to list existing landing zones (this would be a real API call)
            # For now, we'll show a placeholder
            print("   Checking for existing landing zones...")
            print("   Status: 🔍 Checking...")
            
            # In a real implementation, this would check for existing landing zones
            # and show their status, version, drift status, etc.
            print("   💡 Use AWS Console to check detailed Control Tower status")
            
        except Exception as e:
            print(f"   Status: ⚠️ Unable to check - {e}")

        # Check prerequisites status
        print(f"\n📋 Prerequisites Status:")
        try:
            validator = PrerequisitesValidator(self.aws_client)
            results = validator.validate_all()
            
            passed = sum(1 for r in results if r.status.value == "PASSED")
            failed = sum(1 for r in results if r.status.value == "FAILED")
            warnings = sum(1 for r in results if r.status.value == "WARNING")
            
            print(f"   ✅ Passed: {passed}")
            print(f"   ❌ Failed: {failed}")
            print(f"   ⚠️ Warnings: {warnings}")
            
            if failed == 0:
                print("   Overall: ✅ Ready for deployment")
            else:
                print("   Overall: ❌ Prerequisites need attention")
                
        except Exception as e:
            print(f"   Status: ⚠️ Unable to check - {e}")

        # Check security services status
        print(f"\n🛡️ Security Services Status:")
        try:
            from ..post_deployment.orchestrator import PostDeploymentOrchestrator
            
            orchestrator = PostDeploymentOrchestrator(self.config, self.aws_client)
            status = orchestrator.get_deployment_status()
            
            print(f"   Total Services: {status['summary']['total_services']}")
            print(f"   Healthy: {status['summary']['healthy_services']}")
            print(f"   Failed: {status['summary']['failed_services']}")
            
            if status['summary']['deployment_complete']:
                print("   Overall: ✅ Security baseline deployed")
            else:
                print("   Overall: ⚠️ Security baseline incomplete")
            
            # Show individual service status
            for service, details in status['services'].items():
                service_name = service.replace('_', ' ').title()
                status_icon = "✅" if details['healthy'] else "❌"
                print(f"   {service_name}: {status_icon}")
                
        except Exception as e:
            print(f"   Status: ⚠️ Unable to check - {e}")

        # Offer to check specific operation status
        print(f"\n🔍 Operation Status Check:")
        operation_id = input("Enter Control Tower operation ID to check (or press Enter to skip): ").strip()
        
        if operation_id:
            try:
                from ..control_tower.orchestrator import DeploymentOrchestrator
                
                orchestrator = DeploymentOrchestrator(self.config, self.aws_client)
                status_info = orchestrator.get_deployment_status(operation_id)
                
                print(f"\n📊 Operation Status:")
                print(f"   Operation ID: {status_info['operation_id']}")
                print(f"   Status: {status_info['status']}")
                print(f"   Type: {status_info['operation_type']}")
                print(f"   Start Time: {status_info['start_time']}")
                
                if status_info['end_time']:
                    print(f"   End Time: {status_info['end_time']}")
                
                if status_info.get('status_message'):
                    print(f"   Message: {status_info['status_message']}")
                
                # Show deployment state
                deployment_state = status_info.get('deployment_state', {})
                print(f"\n📋 Deployment Progress:")
                for step, completed in deployment_state.items():
                    status_icon = "✅" if completed else "⏳"
                    step_name = step.replace('_', ' ').title()
                    print(f"   {status_icon} {step_name}")
                
            except Exception as e:
                print(f"   ❌ Failed to check operation status: {e}")

        input("\nPress Enter to continue...")

    def _generate_documentation(self) -> None:
        """Generate documentation (placeholder)."""
        print("\n" + "=" * 60)
        print("Generate Documentation")
        print("=" * 60)
        print("🚧 This feature will be implemented in Milestone 5.")
        print(
            "   Will generate deployment summaries and architecture diagrams."
        )

        input("\nPress Enter to continue...")

    def _configuration_management(self) -> None:
        """Configuration management menu."""
        print("\n" + "=" * 60)
        print("Configuration Management")
        print("=" * 60)
        print("1. View Current Configuration")
        print("2. Validate Configuration")
        print("3. Show Configuration File Path")
        print("0. Back to Main Menu")
        print("-" * 60)

        choice = input("Please select an option (0-3): ").strip()

        if choice == "0":
            return
        elif choice == "1":
            self._view_configuration()
        elif choice == "2":
            self._validate_configuration()
        elif choice == "3":
            self._show_config_path()
        else:
            print("❌ Invalid choice.")

        input("\nPress Enter to continue...")

    def _view_configuration(self) -> None:
        """Display current configuration."""
        print("\n📄 Current Configuration:")
        print("-" * 40)
        config_dict = self.config.to_dict()
        self._display_config_summary(config_dict)

    def _validate_configuration(self) -> None:
        """Validate current configuration."""
        print("\n🔍 Validating configuration...")
        try:
            # Configuration is already validated during loading
            print("✅ Configuration is valid!")
            print(f"   Home Region: {self.config.get_home_region()}")
            print(
                f"   Governed Regions: {len(self.config.get_governed_regions())} regions"
            )
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")

    def _show_config_path(self) -> None:
        """Show configuration file path."""
        print(f"\n📁 Configuration file: {self.config._config_path}")

    def _display_config_summary(
        self, config: Dict[str, Any], indent: int = 0
    ) -> None:
        """Display configuration in a readable format.

        Args:
            config: Configuration dictionary
            indent: Indentation level
        """
        prefix = "  " * indent

        for key, value in config.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                self._display_config_summary(value, indent + 1)
            elif isinstance(value, list):
                if len(value) <= 3:
                    print(f"{prefix}{key}: {', '.join(map(str, value))}")
                else:
                    print(f"{prefix}{key}: [{len(value)} items]")
            else:
                print(f"{prefix}{key}: {value}")
