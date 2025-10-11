#!/usr/bin/env python3
"""Configuration setup helper for AWS Control Tower Automation.

This script helps users select and customize configuration templates
for their specific deployment requirements.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any
import yaml


def display_banner():
    """Display setup banner."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AWS Control Tower Configuration Setup                     ║
║                                                                              ║
║              Select and customize a configuration template                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


def get_template_choice() -> str:
    """Get user's template choice."""
    templates = {
        "1": {
            "name": "Minimal Configuration",
            "file": "config-example-minimal.yaml",
            "description": "Single region, basic security, minimal setup"
        },
        "2": {
            "name": "Complete Configuration", 
            "file": "config-example-complete.yaml",
            "description": "Multi-region, standard security, full features"
        },
        "3": {
            "name": "Enterprise Configuration",
            "file": "config-example-enterprise.yaml", 
            "description": "Global regions, strict security, enterprise-grade"
        }
    }
    
    print("Available Configuration Templates:")
    print("-" * 50)
    
    for key, template in templates.items():
        print(f"{key}. {template['name']}")
        print(f"   {template['description']}")
        print()
    
    while True:
        choice = input("Select template (1-3): ").strip()
        if choice in templates:
            return templates[choice]["file"]
        print("Invalid choice. Please select 1, 2, or 3.")


def get_user_inputs() -> Dict[str, Any]:
    """Get required user inputs."""
    print("\nRequired Configuration:")
    print("-" * 30)
    
    inputs = {}
    
    # Email addresses
    inputs["log_archive_email"] = input("Log Archive account email: ").strip()
    inputs["audit_email"] = input("Audit account email: ").strip()
    
    # Home region
    default_region = "us-east-1"
    region = input(f"Home region [{default_region}]: ").strip()
    inputs["home_region"] = region if region else default_region
    
    return inputs


def customize_config(template_file: str, inputs: Dict[str, Any]) -> None:
    """Customize configuration with user inputs."""
    config_dir = Path("config")
    template_path = config_dir / template_file
    output_path = Path("config.yaml")
    
    # Load template
    with open(template_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Apply customizations
    config["aws"]["home_region"] = inputs["home_region"]
    config["accounts"]["log_archive"]["email"] = inputs["log_archive_email"]
    config["accounts"]["audit"]["email"] = inputs["audit_email"]
    
    # Write customized config
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ Configuration saved to: {output_path}")


def main():
    """Main setup function."""
    display_banner()
    
    # Check if config.yaml already exists
    if Path("config.yaml").exists():
        overwrite = input("config.yaml already exists. Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    # Get template choice
    template_file = get_template_choice()
    
    # Get user inputs
    inputs = get_user_inputs()
    
    # Customize and save config
    customize_config(template_file, inputs)
    
    print("\nNext Steps:")
    print("1. Review and edit config.yaml if needed")
    print("2. Run: python src/controltower-baseline.py --validate-only")
    print("3. Run: python src/controltower-baseline.py")


if __name__ == "__main__":
    main()
