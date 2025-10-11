"""Automated architecture diagram generation for Control Tower deployment.

This module handles generation of Control Tower architecture diagrams,
security services topology, and organizational structure visualization.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from ..core.config import Configuration
from ..core.aws_client import AWSClientManager


logger = logging.getLogger(__name__)


class DiagramGenerationError(Exception):
    """Raised when diagram generation fails."""
    pass


class DiagramGenerator:
    """Automated architecture diagram generation for Control Tower deployment."""
    
    def __init__(self, config: Configuration, aws_client: AWSClientManager):
        """Initialize diagram generator.
        
        Args:
            config: Configuration instance
            aws_client: AWS client manager instance
        """
        self.config = config
        self.aws_client = aws_client
        
    def generate_control_tower_architecture(self, output_dir: Path = None) -> Path:
        """Generate Control Tower architecture diagram with accounts and OUs.
        
        Args:
            output_dir: Output directory for diagram (defaults to docs/)
            
        Returns:
            Path to the generated architecture diagram
            
        Raises:
            DiagramGenerationError: When diagram generation fails
        """
        try:
            # Import diagrams here to avoid dependency issues if not installed
            from diagrams import Diagram, Cluster, Edge
            from diagrams.aws.management import Organizations, ControlTower
            from diagrams.aws.security import IAM
            from diagrams.aws.storage import S3
            
            if output_dir is None:
                output_dir = Path("docs")
            
            output_dir.mkdir(exist_ok=True)
            
            with Diagram("Control Tower Architecture", 
                        filename=str(output_dir / "control_tower_architecture"),
                        show=False, direction="TB"):
                
                # Management Account
                with Cluster("Management Account"):
                    mgmt_ct = ControlTower("Control Tower")
                    mgmt_orgs = Organizations("Organizations")
                    mgmt_iam = IAM("IAM Roles")
                
                # Security OU
                with Cluster("Security OU"):
                    audit_account = S3("Audit Account")
                    log_archive = S3("Log Archive")
                
                # Sandbox OU  
                with Cluster("Sandbox OU"):
                    sandbox_accounts = S3("Sandbox Accounts")
                
                # Connections
                mgmt_orgs >> Edge(label="manages") >> [audit_account, log_archive, sandbox_accounts]
                mgmt_ct >> Edge(label="governs") >> mgmt_orgs
                mgmt_iam >> Edge(label="enables") >> mgmt_ct
            
            diagram_path = output_dir / "control_tower_architecture.png"
            logger.info(f"Control Tower architecture diagram saved to {diagram_path}")
            
            return diagram_path
            
        except ImportError:
            raise DiagramGenerationError("diagrams package not installed. Install with: pip install diagrams")
        except Exception as e:
            raise DiagramGenerationError(f"Failed to generate Control Tower architecture: {e}")
    
    def generate_security_topology(self, output_dir: Path = None) -> Path:
        """Generate security services topology diagram.
        
        Args:
            output_dir: Output directory for diagram (defaults to docs/)
            
        Returns:
            Path to the generated security topology diagram
            
        raises:
            DiagramGenerationError: When diagram generation fails
        """
        try:
            from diagrams import Diagram, Cluster, Edge
            from diagrams.aws.security import GuardDuty, SecurityHub, Config
            from diagrams.aws.management import Organizations
            
            if output_dir is None:
                output_dir = Path("docs")
            
            output_dir.mkdir(exist_ok=True)
            
            with Diagram("Security Services Topology",
                        filename=str(output_dir / "security_topology"),
                        show=False, direction="LR"):
                
                # Organization
                orgs = Organizations("AWS Organizations")
                
                # Security Services
                with Cluster("Security Services"):
                    config = Config("AWS Config\n(Aggregator)")
                    guardduty = GuardDuty("GuardDuty\n(Delegated Admin)")
                    security_hub = SecurityHub("Security Hub\n(Standards)")
                
                # Data flow
                orgs >> Edge(label="accounts") >> config
                orgs >> Edge(label="accounts") >> guardduty
                orgs >> Edge(label="accounts") >> security_hub
                
                config >> Edge(label="compliance data") >> security_hub
                guardduty >> Edge(label="findings") >> security_hub
            
            diagram_path = output_dir / "security_topology.png"
            logger.info(f"Security topology diagram saved to {diagram_path}")
            
            return diagram_path
            
        except ImportError:
            raise DiagramGenerationError("diagrams package not installed. Install with: pip install diagrams")
        except Exception as e:
            raise DiagramGenerationError(f"Failed to generate security topology: {e}")
    
    def generate_organization_structure(self, output_dir: Path = None) -> Path:
        """Generate organization structure diagram with hierarchical layout.
        
        Args:
            output_dir: Output directory for diagram (defaults to docs/)
            
        Returns:
            Path to the generated organization structure diagram
            
        Raises:
            DiagramGenerationError: When diagram generation fails
        """
        try:
            from diagrams import Diagram, Cluster, Edge
            from diagrams.aws.management import Organizations
            from diagrams.aws.general import General
            
            if output_dir is None:
                output_dir = Path("docs")
            
            output_dir.mkdir(exist_ok=True)
            
            with Diagram("Organization Structure",
                        filename=str(output_dir / "organization_structure"),
                        show=False, direction="TB"):
                
                # Root
                root = Organizations("Root Organization")
                
                # Core OUs
                with Cluster("Core"):
                    security_ou = General("Security OU")
                    
                # Workload OUs
                with Cluster("Workloads"):
                    sandbox_ou = General("Sandbox OU")
                
                # Connections
                root >> Edge(label="contains") >> [security_ou, sandbox_ou]
            
            diagram_path = output_dir / "organization_structure.png"
            logger.info(f"Organization structure diagram saved to {diagram_path}")
            
            return diagram_path
            
        except ImportError:
            raise DiagramGenerationError("diagrams package not installed. Install with: pip install diagrams")
        except Exception as e:
            raise DiagramGenerationError(f"Failed to generate organization structure: {e}")
    
    def generate_all_diagrams(self, output_dir: Path = None) -> List[Path]:
        """Generate all architecture diagrams.
        
        Args:
            output_dir: Output directory for diagrams (defaults to docs/)
            
        Returns:
            List of paths to all generated diagrams
            
        Raises:
            DiagramGenerationError: When any diagram generation fails
        """
        try:
            diagrams = []
            
            diagrams.append(self.generate_control_tower_architecture(output_dir))
            diagrams.append(self.generate_security_topology(output_dir))
            diagrams.append(self.generate_organization_structure(output_dir))
            
            logger.info(f"Generated {len(diagrams)} architecture diagrams")
            return diagrams
            
        except Exception as e:
            raise DiagramGenerationError(f"Failed to generate all diagrams: {e}")
