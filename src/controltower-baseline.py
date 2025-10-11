#!/usr/bin/env python3
"""AWS Control Tower Automation - Main Entry Point.

This is the single entry point for AWS Control Tower deployment automation
with complete security baseline configuration.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from core.config import Configuration, ConfigurationError
from core.aws_client import AWSClientManager
from core.interactive import InteractiveMenu
from core.validator import PrerequisitesValidator


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="AWS Control Tower Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Auto-detect config.yaml, start interactive mode
  %(prog)s config.yaml              # Use specific configuration file
  %(prog)s --validate-only          # Only validate prerequisites
  %(prog)s --version                # Show version information

For more information, visit: https://github.com/aws-control-tower-automation
        """,
    )

    parser.add_argument(
        "config_file",
        nargs="?",
        help="Path to configuration file (default: auto-detect config.yaml)",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate prerequisites, do not start interactive mode",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="AWS Control Tower Automation v1.0.0",
    )

    parser.add_argument(
        "--profile", help="AWS profile name to use for credentials"
    )

    parser.add_argument(
        "--region", help="AWS region to use (overrides configuration file)"
    )

    return parser.parse_args()


def auto_detect_config() -> Optional[str]:
    """Auto-detect configuration file in current directory.

    Returns:
        Path to configuration file if found, None otherwise
    """
    # Check for config.yaml in current directory
    if Path("config.yaml").exists():
        return "config.yaml"

    # Check for config/settings.yaml
    if Path("config/settings.yaml").exists():
        return "config/settings.yaml"

    return None


def display_banner() -> None:
    """Display application banner."""
    print(
        """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AWS Control Tower Automation Tool                         ║
║                                                                              ║
║  Automated deployment of AWS Control Tower with complete security baseline  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    )


def validate_prerequisites(aws_client: AWSClientManager) -> bool:
    """Validate all prerequisites for Control Tower deployment.

    Args:
        aws_client: Configured AWS client manager

    Returns:
        True if all prerequisites are met, False otherwise
    """
    print("Validating prerequisites...")
    print("-" * 50)

    validator = PrerequisitesValidator(aws_client)
    results = validator.validate_all()

    # Display results
    for result in results:
        status_symbol = {
            "PASSED": "✅",
            "FAILED": "❌",
            "WARNING": "⚠️",
            "SKIPPED": "⏭️",
        }.get(result.status.value, "❓")

        print(f"{status_symbol} {result.validator_name}: {result.message}")

        if result.remediation_steps:
            print("   Remediation steps:")
            for step in result.remediation_steps:
                print(f"   • {step}")
            print()

    print("-" * 50)

    # Check if ready for deployment
    is_ready = validator.is_ready_for_deployment(results)

    if is_ready:
        print("✅ All prerequisites validated successfully!")
        print("   Ready for Control Tower deployment.")
    else:
        print("❌ Prerequisites validation failed.")
        print("   Please address the issues above before proceeding.")

    return is_ready


def main() -> int:
    """Main application entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Display banner
        display_banner()

        # Determine configuration file path
        config_path = args.config_file
        if not config_path:
            config_path = auto_detect_config()

        if not config_path:
            print("❌ No configuration file found.")
            print(
                "   Please create config.yaml or specify a configuration file."
            )
            print("   Use --help for more information.")
            return 1

        print(f"📄 Using configuration file: {config_path}")

        # Load configuration
        try:
            config = Configuration(config_path)
        except ConfigurationError as e:
            print(f"❌ Configuration error: {e}")
            return 1

        # Apply command line overrides
        if args.region:
            # Override region in configuration
            import os

            os.environ["AWS_REGION"] = args.region
            config = Configuration(config_path)  # Reload with override

        # Initialize AWS client manager
        try:
            aws_client = AWSClientManager(profile_name=args.profile)
        except Exception as e:
            print(f"❌ AWS client initialization failed: {e}")
            return 1

        # Validate prerequisites
        prerequisites_ok = validate_prerequisites(aws_client)

        if args.validate_only:
            return 0 if prerequisites_ok else 1

        if not prerequisites_ok:
            print(
                "\n❌ Cannot proceed with deployment due to prerequisite failures."
            )
            print(
                "   Use --validate-only to check prerequisites without starting interactive mode."
            )
            return 1

        # Start interactive menu
        print("\n🚀 Starting interactive mode...")
        menu = InteractiveMenu(config, aws_client)
        menu.run()

        return 0

    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user.")
        return 130

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("   Please check your configuration and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
