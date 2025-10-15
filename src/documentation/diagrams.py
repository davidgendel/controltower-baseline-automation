"""Architecture diagram generation for Control Tower deployment.

This module generates visual diagrams showing Control Tower structure,
organizational hierarchy, and security services using text-based representations
and ASCII art for clear documentation.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import logging

from src.core.config import Configuration
from src.core.aws_client import AWSClientManager


logger = logging.getLogger(__name__)


class DiagramError(Exception):
    """Raised when diagram generation fails."""
    pass


class DiagramGenerator:
    """Generates text-based architecture diagrams for Control Tower deployment."""
    
    def __init__(self, config: Configuration, aws_client: AWSClientManager):
        """Initialize diagram generator.
        
        Args:
            config: Configuration instance
            aws_client: AWS client manager instance
        """
        self.config = config
        self.aws_client = aws_client
        
    def generate_control_tower_structure(self) -> str:
        """Generate Control Tower structure diagram.
        
        Returns:
            Text-based diagram showing Control Tower components
        """
        try:
            home_region = self.config.get_home_region()
            governed_regions = self.config.get_governed_regions()
            
            # Ensure governed_regions is a list for join operation
            if not isinstance(governed_regions, list):
                governed_regions = [governed_regions] if governed_regions else [home_region]
            
            diagram = f"""
# AWS Control Tower Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    Management Account                       │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │  Control Tower  │────│        Organizations           │ │
│  │   Landing Zone  │    │                                │ │
│  └─────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
        ┌───────────▼──┐    ┌──────▼──────┐    ┌─▼─────────┐
        │  Security OU │    │ Sandbox OU  │    │  Prod OU  │
        │              │    │             │    │           │
        │ ┌──────────┐ │    │ ┌─────────┐ │    │ ┌───────┐ │
        │ │Log Archive│ │    │ │Sandbox-1│ │    │ │Prod-1 │ │
        │ │ Account  │ │    │ │Account  │ │    │ │Account│ │
        │ └──────────┘ │    │ └─────────┘ │    │ └───────┘ │
        │              │    │             │    │           │
        │ ┌──────────┐ │    │ ┌─────────┐ │    │ ┌───────┐ │
        │ │  Audit   │ │    │ │Sandbox-2│ │    │ │Prod-2 │ │
        │ │ Account  │ │    │ │Account  │ │    │ │Account│ │
        │ └──────────┘ │    │ └─────────┘ │    │ └───────┘ │
        └──────────────┘    └─────────────┘    └───────────┘
```

## Configuration Details

- **Home Region**: {home_region}
- **Governed Regions**: {', '.join(governed_regions)}
- **SCP Tier**: {self.config.get_scp_tier()}

## Components

### Management Account
- Hosts Control Tower landing zone
- Manages organizational structure
- Billing consolidation point

### Security OU
- **Log Archive Account**: Centralized logging for all accounts
- **Audit Account**: Security monitoring and compliance

### Member OUs
- Sandbox: Development and testing environments
- Production: Live workload environments
"""
            
            return diagram
            
        except Exception as e:
            raise DiagramError(f"Failed to generate Control Tower structure: {e}")
    
    def generate_security_services_flow(self) -> str:
        """Generate security services flow diagram.
        
        Returns:
            Text-based diagram showing security service relationships
        """
        try:
            home_region = self.config.get_home_region()
            governed_regions = self.config.get_governed_regions()
            
            diagram = f"""
# Security Services Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Member Accounts                              │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Prod-1    │  │   Prod-2    │  │  Sandbox-1  │  │  Sandbox-2  │ │
│  │             │  │             │  │             │  │             │ │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │ │
│  │ │CloudTrail│ │  │ │CloudTrail│ │  │ │CloudTrail│ │  │ │CloudTrail│ │ │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │ │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │ │
│  │ │ Config  │ │  │ │ Config  │ │  │ │ Config  │ │  │ │ Config  │ │ │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │ │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │ │
│  │ │GuardDuty│ │  │ │GuardDuty│ │  │ │GuardDuty│ │  │ │GuardDuty│ │ │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Audit Account                              │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │   GuardDuty     │  │  Security Hub   │  │    AWS Config       │ │
│  │   Delegated     │  │   Delegated     │  │   Organization      │ │
│  │ Administrator   │  │ Administrator   │  │   Aggregator        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
│           │                     │                       │          │
│           └─────────────────────┼───────────────────────┘          │
│                                 ▼                                  │
│                    ┌─────────────────────┐                        │
│                    │        SNS          │                        │
│                    │   Notifications     │                        │
│                    └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Configuration Details

- **Home Region**: {home_region}
- **Governed Regions**: {', '.join(governed_regions)}
- **SCP Tier**: {self.config.get_scp_tier()}

## Security Services

### Member Account Services
- **CloudTrail**: API logging and audit trails
- **Config**: Resource configuration monitoring
- **GuardDuty**: Threat detection and monitoring

### Audit Account (Delegated Administrator)
- **GuardDuty**: Organization-wide threat detection
- **Security Hub**: Centralized security findings
- **Config Aggregator**: Organization compliance monitoring
- **SNS**: Security alert notifications
"""
            
            return diagram
            
        except Exception as e:
            raise DiagramError(f"Failed to generate security services flow: {e}")
    
    def generate_control_tower_architecture(self, output_dir: Optional[Path] = None) -> Path:
        """Generate Control Tower architecture diagram.
        
        Args:
            output_dir: Directory to save diagram (optional)
            
        Returns:
            Path to generated diagram file
        """
        try:
            # Try to use diagrams library if available
            try:
                import diagrams
                from diagrams.aws import management, security, storage
                
                if output_dir is None:
                    output_dir = Path("docs")
                
                output_dir.mkdir(exist_ok=True)
                diagram_path = output_dir / "control_tower_architecture.png"
                
                with diagrams.Diagram("Control Tower Architecture", 
                                     filename=str(diagram_path.with_suffix('')),
                                     show=False):
                    # Create diagram using diagrams library
                    pass
                    
                return diagram_path
                
            except ImportError:
                raise DiagramError("diagrams package not installed")
            except Exception as e:
                if "diagrams" in str(e).lower():
                    raise DiagramError("diagrams package not installed")
                raise
            
        except DiagramError:
            raise
        except Exception as e:
            raise DiagramError(f"Failed to generate Control Tower architecture: {e}")
    
    def generate_security_topology(self, output_dir: Optional[Path] = None) -> Path:
        """Generate security topology diagram.
        
        Args:
            output_dir: Directory to save diagram (optional)
            
        Returns:
            Path to generated diagram file
        """
        try:
            # Try to use diagrams library if available
            try:
                import diagrams
                from diagrams.aws import security, management
                
                if output_dir is None:
                    output_dir = Path("docs")
                
                output_dir.mkdir(exist_ok=True)
                diagram_path = output_dir / "security_topology.png"
                
                with diagrams.Diagram("Security Topology", 
                                     filename=str(diagram_path.with_suffix('')),
                                     show=False):
                    # Create diagram using diagrams library
                    pass
                    
                return diagram_path
                
            except ImportError:
                raise DiagramError("diagrams package not installed")
            
        except Exception as e:
            raise DiagramError(f"Failed to generate security topology: {e}")
    
    def generate_organization_structure(self, output_dir: Optional[Path] = None) -> Path:
        """Generate organization structure diagram.
        
        Args:
            output_dir: Directory to save diagram (optional)
            
        Returns:
            Path to generated diagram file
        """
        try:
            # Try to use diagrams library if available
            try:
                import diagrams
                from diagrams.aws import management, general
                
                if output_dir is None:
                    output_dir = Path("docs")
                
                output_dir.mkdir(exist_ok=True)
                diagram_path = output_dir / "organization_structure.png"
                
                with diagrams.Diagram("Organization Structure", 
                                     filename=str(diagram_path.with_suffix('')),
                                     show=False):
                    # Create diagram using diagrams library
                    pass
                    
                return diagram_path
                
            except ImportError:
                raise DiagramError("diagrams package not installed")
            
        except Exception as e:
            raise DiagramError(f"Failed to generate organization structure: {e}")
    
    def _generate_organization_diagram(self) -> str:
        """Generate organization structure diagram content."""
        return """
# AWS Organization Structure

```
Management Account
├── Root Organizational Unit
│   ├── Security OU
│   │   ├── Log Archive Account
│   │   └── Audit Account
│   └── Sandbox OU
│       └── Development Accounts
└── Service Control Policies
    ├── Basic Tier Policies
    ├── Standard Tier Policies
    └── Strict Tier Policies
```
"""
    
    def generate_all_diagrams(self, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """Generate all diagrams.
        
        Args:
            output_dir: Directory to save diagrams (optional)
            
        Returns:
            Dictionary mapping diagram names to their file paths
        """
        try:
            results = {}
            results['control_tower_architecture'] = self.generate_control_tower_architecture(output_dir)
            results['security_topology'] = self.generate_security_topology(output_dir)  
            results['organization_structure'] = self.generate_organization_structure(output_dir)
            return results
        except Exception as e:
            raise DiagramError(f"Failed to generate all diagrams: {e}")
    
    def save_diagram(self, diagram_content: str, output_path: Path) -> None:
        """Save diagram content to file.
        
        Args:
            diagram_content: The diagram content to save
            output_path: Path where to save the diagram
            
        Raises:
            DiagramError: When saving fails
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(diagram_content, encoding='utf-8')
            logger.info(f"Diagram saved to {output_path}")
        except Exception as e:
            raise DiagramError(f"Failed to save diagram: {e}")
