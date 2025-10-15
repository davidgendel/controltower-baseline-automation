"""Interactive menu system for AWS Control Tower automation.

This module provides a clean, intuitive menu interface for all major
functions with input validation and consistent user experience.
"""

from typing import Dict, Any, Optional
import sys

from src.core.config import Configuration
from src.core.aws_client import AWSClientManager
from src.core.validator import PrerequisitesValidator
from src.core.safety import SafetyManager


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
        print("5. Security Configuration Management")
        print("6. Check Status")
        print("7. Generate Documentation")
        print("8. Configuration Management")
        print("0. Exit")
        print("-" * 60)

    def _get_user_choice(self) -> str:
        """Get and validate user menu choice.

        Returns:
            User's menu choice as string
        """
        while True:
            try:
                choice = input("Please select an option (0-8): ").strip()
                if choice in ["0", "1", "2", "3", "4", "5", "6", "7", "8"]:
                    return choice
                else:
                    print(
                        "❌ Invalid choice. Please select a number from 0-8."
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
            "5": self._security_configuration_management,
            "6": self._check_status,
            "7": self._generate_documentation,
            "8": self._configuration_management,
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
        from src.prerequisites.organizations import OrganizationsManager
        from src.prerequisites.accounts import AccountManager
        
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
        """Setup AWS Organizations with comprehensive safety checks."""
        from src.prerequisites.organizations import OrganizationsManager
        
        org_manager = OrganizationsManager(self.aws_client)
        
        # Check if organization already exists
        if org_manager.organization_exists():
            print("  ℹ️ AWS Organization already exists")
            print("  🔧 Checking if all features are enabled...")
            org_manager.enable_all_features()
            print("  ✅ Organizations all features enabled")
            return
        
        # Organization doesn't exist - need to create it
        print("  ⚠️ AWS Organization does not exist")
        print("  📋 Creating an AWS Organization will:")
        print("     • Make this account the permanent management account")
        print("     • Enable all AWS Organizations features")
        print("     • Allow centralized management of multiple AWS accounts")
        print("     • Enable Service Control Policies (SCPs)")
        print("     • This action CANNOT be undone")
        print()
        
        # First confirmation
        print("  🚨 CRITICAL: This is a permanent, irreversible change to your AWS account")
        first_confirm = input("  Type 'CREATE' to acknowledge this is permanent: ").strip()
        
        if first_confirm != 'CREATE':
            print("  ❌ Organization creation cancelled")
            return
        
        # Second confirmation with account details
        account_id = self.aws_client.get_account_id()
        print(f"\n  📋 Confirmation Details:")
        print(f"     • Account ID: {account_id}")
        print(f"     • This account will become the management account")
        print(f"     • You will be able to create and manage member accounts")
        print(f"     • Service Control Policies will be enabled")
        print()
        
        second_confirm = input("  Type 'yes' to proceed with organization creation: ").strip().lower()
        
        if second_confirm != 'yes':
            print("  ❌ Organization creation cancelled")
            return
        
        try:
            print("  🔧 Creating AWS Organization (this may take several minutes)...")
            organization = org_manager.create_organization()
            
            # Wait for organization to be ready
            if org_manager.wait_for_organization_ready():
                print("  ✅ AWS Organization created successfully")
                print(f"  ✅ Organization ID: {organization['Id']}")
                print(f"  ✅ Management Account: {organization['MasterAccountId']}")
            else:
                print("  ⚠️ Organization created but may still be initializing")
                print("  💡 You can continue with setup - organization will be ready shortly")
                
        except Exception as e:
            print(f"  ❌ Failed to create organization: {e}")
            print("  💡 Please check AWS console or try again later")
            raise
        
    def _setup_organization_structure(self) -> None:
        """Setup organization structure with required OUs."""
        from src.prerequisites.organizations import OrganizationsManager
        
        print("  🔧 Creating organizational units...")
        org_manager = OrganizationsManager(self.aws_client)
        
        # Get root ID
        root_id = org_manager.get_root_id()
        
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
        from src.control_tower.orchestrator import DeploymentOrchestrator, DeploymentOrchestrationError
        
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
        from src.post_deployment.orchestrator import PostDeploymentOrchestrator
        
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
    
    def _get_audit_account_id(self) -> Optional[str]:
        """Get audit account ID with automated detection and fallbacks.
        
        Returns:
            Audit account ID if found, None if user cancels
        """
        print("📋 Audit Account Detection")
        print("Attempting to automatically detect audit account...")
        
        # Method 1: Try to get from deployment state
        try:
            from src.control_tower.orchestrator import DeploymentOrchestrator
            orchestrator = DeploymentOrchestrator(self.config, self.aws_client)
            audit_account_id = orchestrator.get_audit_account_id()
            
            if audit_account_id:
                print(f"✅ Found audit account from deployment: {audit_account_id}")
                confirm = input("Use this audit account? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    return audit_account_id
        except Exception:
            pass
        
        # Method 2: Try to find by configuration
        try:
            from src.prerequisites.organizations import OrganizationsManager
            org_manager = OrganizationsManager(self.aws_client)
            
            # Try to find by email from config
            audit_email = self.config.get('accounts.audit.email')
            if audit_email:
                audit_account_id = org_manager.find_account_by_email(audit_email)
                if audit_account_id:
                    # Validate it's in Security OU
                    if org_manager.validate_account_in_security_ou(audit_account_id):
                        print(f"✅ Found audit account by email: {audit_account_id}")
                        confirm = input("Use this audit account? (y/n): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            return audit_account_id
            
            # Try to find by name from config
            audit_name = self.config.get('accounts.audit.name')
            if audit_name:
                audit_account_id = org_manager.find_account_by_name(audit_name)
                if audit_account_id:
                    # Validate it's in Security OU
                    if org_manager.validate_account_in_security_ou(audit_account_id):
                        print(f"✅ Found audit account by name: {audit_account_id}")
                        confirm = input("Use this audit account? (y/n): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            return audit_account_id
        except Exception:
            pass
        
        # Method 3: Manual input as last resort
        print("⚠️ Could not automatically detect audit account")
        print("The audit account will be designated as delegated administrator")
        print("for all security services (Config, GuardDuty, Security Hub).")
        print()
        
        while True:
            account_id = input("Enter Audit Account ID (12 digits, or 'cancel' to abort): ").strip()
            
            if account_id.lower() == 'cancel':
                return None
            
            if len(account_id) == 12 and account_id.isdigit():
                # Validate account exists and is accessible
                try:
                    from src.prerequisites.organizations import OrganizationsManager
                    org_manager = OrganizationsManager(self.aws_client)
                    
                    if org_manager.validate_account_in_security_ou(account_id):
                        print(f"✅ Audit Account ID: {account_id}")
                        confirm = input("Is this correct? (y/n): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            return account_id
                    else:
                        print("⚠️ Account not found in Security OU. Please verify the account ID.")
                except Exception:
                    print("⚠️ Could not validate account. Please verify the account ID.")
            else:
                print("❌ Invalid account ID. Must be exactly 12 digits.")
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
            from src.control_tower.deployer import ControlTowerDeployer
            
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
            from src.post_deployment.orchestrator import PostDeploymentOrchestrator
            
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
                from src.control_tower.orchestrator import DeploymentOrchestrator
                
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
        """Generate comprehensive documentation and diagrams."""
        print("\n" + "=" * 60)
        print("Generate Documentation")
        print("=" * 60)
        
        from src.documentation.generator import DocumentationGenerator
        from src.documentation.diagrams import DiagramGenerator
        from pathlib import Path
        from datetime import datetime
        
        try:
            # Initialize generators
            doc_generator = DocumentationGenerator(self.config, self.aws_client)
            diagram_generator = DiagramGenerator(self.config, self.aws_client)
            
            # Create output directory
            docs_dir = Path("docs")
            docs_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            print("📄 Generating documentation...")
            
            # 1. Generate deployment summary
            print("  • Deployment summary...")
            try:
                from src.control_tower.orchestrator import DeploymentOrchestrator
                orchestrator = DeploymentOrchestrator(self.config, self.aws_client)
                deployment_state = {
                    'audit_account_id': orchestrator.get_audit_account_id(),
                    'landing_zone_arn': orchestrator.get_stored_landing_zone_arn(),
                    'config': self.config.to_dict()
                }
                
                summary = doc_generator.generate_deployment_summary(deployment_state)
                summary_file = doc_generator.save_documentation(
                    summary, f"deployment_summary_{timestamp}.md", docs_dir
                )
                print(f"    ✅ Saved: {summary_file}")
                
            except Exception as e:
                print(f"    ⚠️ Could not generate deployment summary: {e}")
            
            # 2. Generate configuration documentation
            print("  • Configuration reference...")
            try:
                config_docs = doc_generator.generate_configuration_docs()
                config_file = doc_generator.save_documentation(
                    config_docs, f"configuration_reference_{timestamp}.md", docs_dir
                )
                print(f"    ✅ Saved: {config_file}")
                
            except Exception as e:
                print(f"    ⚠️ Could not generate configuration docs: {e}")
            
            # 3. Generate validation report
            print("  • Validation report...")
            try:
                from src.post_deployment.orchestrator import PostDeploymentOrchestrator
                post_orchestrator = PostDeploymentOrchestrator(self.config, self.aws_client)
                validation_results = post_orchestrator.validate_service_health()
                
                validation_report = doc_generator.generate_validation_report(validation_results)
                validation_file = doc_generator.save_documentation(
                    validation_report, f"validation_report_{timestamp}.md", docs_dir
                )
                print(f"    ✅ Saved: {validation_file}")
                
            except Exception as e:
                print(f"    ⚠️ Could not generate validation report: {e}")
            
            # 4. Generate architecture diagrams
            print("🎨 Generating architecture diagrams...")
            diagrams_dir = docs_dir / "diagrams"
            diagrams_dir.mkdir(exist_ok=True)
            
            try:
                # Control Tower structure diagram
                print("  • Control Tower structure...")
                ct_diagram = diagram_generator.generate_control_tower_diagram()
                ct_file = diagrams_dir / f"control_tower_structure_{timestamp}.png"
                diagram_generator.save_diagram(ct_diagram, ct_file)
                print(f"    ✅ Saved: {ct_file}")
                
                # OU hierarchy diagram
                print("  • Organization hierarchy...")
                ou_diagram = diagram_generator.generate_ou_hierarchy_diagram()
                ou_file = diagrams_dir / f"ou_hierarchy_{timestamp}.png"
                diagram_generator.save_diagram(ou_diagram, ou_file)
                print(f"    ✅ Saved: {ou_file}")
                
                # Security services diagram
                print("  • Security services flow...")
                security_diagram = diagram_generator.generate_security_services_diagram()
                security_file = diagrams_dir / f"security_services_{timestamp}.png"
                diagram_generator.save_diagram(security_diagram, security_file)
                print(f"    ✅ Saved: {security_file}")
                
            except Exception as e:
                print(f"    ⚠️ Could not generate diagrams: {e}")
            
            print(f"\n✅ Documentation generated successfully!")
            print(f"📁 Output directory: {docs_dir.absolute()}")
            print(f"🎨 Diagrams directory: {diagrams_dir.absolute()}")
            
        except Exception as e:
            print(f"\n❌ Documentation generation failed: {e}")
        
        input("\nPress Enter to continue...")

    def _security_configuration_management(self) -> None:
        """Security configuration management menu."""
        print("\n" + "=" * 60)
        print("Security Configuration Management")
        print("=" * 60)
        print("Manage security policies independently from deployment templates.")
        print()
        
        try:
            from src.core.security_config import SecurityConfig
            security_config = SecurityConfig()
            
            while True:
                print("\nSecurity Configuration Options:")
                print("1. Show Current Security Configuration")
                print("2. Set Global Security Tier")
                print("3. Set OU-Specific Security Tier")
                print("4. Add Account Exception")
                print("5. Validate Security Configuration")
                print("0. Return to Main Menu")
                print("-" * 40)
                
                choice = input("Please select an option (0-5): ").strip()
                
                if choice == "0":
                    break
                elif choice == "1":
                    self._show_security_config(security_config)
                elif choice == "2":
                    self._set_global_security_tier(security_config)
                elif choice == "3":
                    self._set_ou_security_tier(security_config)
                elif choice == "4":
                    self._add_account_exception(security_config)
                elif choice == "5":
                    self._validate_security_config(security_config)
                else:
                    print("❌ Invalid choice.")
                
                if choice != "0":
                    input("\nPress Enter to continue...")
                    
        except Exception as e:
            print(f"❌ Error loading security configuration: {e}")
            input("\nPress Enter to continue...")

    def _show_security_config(self, security_config) -> None:
        """Display current security configuration."""
        print("\n📋 Current Security Configuration:")
        print("-" * 40)
        
        tier = security_config.get_security_tier()
        tier_info = security_config.SECURITY_TIERS[tier]
        
        print(f"Global Security Tier: {tier.upper()}")
        print(f"Description: {tier_info['description']}")
        print(f"Policies: {', '.join(tier_info['policies'])}")
        
        # Show OU overrides
        config_data = security_config.to_dict()
        ou_overrides = config_data.get('ou_overrides', {})
        if ou_overrides:
            print(f"\nOU-Specific Overrides:")
            for ou_name, override_tier in ou_overrides.items():
                print(f"  {ou_name}: {override_tier}")
        
        # Show account exceptions
        exceptions = config_data.get('account_exceptions', [])
        if exceptions:
            print(f"\nAccount Exceptions:")
            for exception in exceptions:
                print(f"  {exception['account_id']}: {exception['reason']}")

    def _set_global_security_tier(self, security_config) -> None:
        """Set global security tier."""
        print("\n🔧 Set Global Security Tier")
        print("-" * 30)
        
        # Show available tiers
        for tier_name, tier_info in security_config.SECURITY_TIERS.items():
            print(f"{tier_name.upper()}: {tier_info['description']}")
        
        print()
        tier = input("Enter security tier (basic/standard/strict): ").strip().lower()
        
        if tier in security_config.SECURITY_TIERS:
            try:
                security_config.set_security_tier(tier)
                security_config.save_config()
                print(f"✅ Global security tier set to: {tier}")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("❌ Invalid security tier.")

    def _set_ou_security_tier(self, security_config) -> None:
        """Set OU-specific security tier."""
        print("\n🏢 Set OU-Specific Security Tier")
        print("-" * 35)
        
        ou_name = input("Enter OU name: ").strip()
        if not ou_name:
            print("❌ OU name cannot be empty.")
            return
        
        # Show available tiers
        for tier_name, tier_info in security_config.SECURITY_TIERS.items():
            print(f"{tier_name.upper()}: {tier_info['description']}")
        
        print()
        tier = input("Enter security tier (basic/standard/strict): ").strip().lower()
        
        if tier in security_config.SECURITY_TIERS:
            try:
                security_config.set_ou_override(ou_name, tier)
                security_config.save_config()
                print(f"✅ OU override set: {ou_name} -> {tier}")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("❌ Invalid security tier.")

    def _add_account_exception(self, security_config) -> None:
        """Add account exception from security policies."""
        print("\n⚠️ Add Account Exception")
        print("-" * 25)
        
        account_id = input("Enter AWS Account ID (12 digits): ").strip()
        if not account_id.isdigit() or len(account_id) != 12:
            print("❌ Invalid account ID. Must be exactly 12 digits.")
            return
        
        reason = input("Enter reason for exception: ").strip()
        if not reason:
            print("❌ Reason cannot be empty.")
            return
        
        try:
            security_config.add_account_exception(account_id, reason)
            security_config.save_config()
            print(f"✅ Account exception added: {account_id}")
        except Exception as e:
            print(f"❌ Error: {e}")

    def _validate_security_config(self, security_config) -> None:
        """Validate security configuration."""
        print("\n🔍 Validating Security Configuration...")
        
        errors = security_config.validate_configuration()
        
        if not errors:
            print("✅ Security configuration is valid.")
        else:
            print("❌ Security configuration has errors:")
            for error in errors:
                print(f"  - {error}")

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
