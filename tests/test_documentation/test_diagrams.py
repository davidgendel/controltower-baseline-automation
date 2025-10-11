"""Unit tests for diagram generator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import sys

from src.documentation.diagrams import DiagramGenerator, DiagramGenerationError
from src.core.config import Configuration
from src.core.aws_client import AWSClientManager


@pytest.fixture
def mock_config():
    config = Mock(spec=Configuration)
    config.get_home_region.return_value = 'us-east-1'
    config.get_governed_regions.return_value = ['us-east-1', 'us-west-2']
    return config


@pytest.fixture
def mock_aws_client():
    client = Mock(spec=AWSClientManager)
    client.account_id = '123456789012'
    return client


@pytest.fixture
def diagram_generator(mock_config, mock_aws_client):
    return DiagramGenerator(mock_config, mock_aws_client)


class TestDiagramGenerator:
    
    def test_generate_control_tower_architecture_success(self, diagram_generator):
        """Test successful Control Tower architecture diagram generation."""
        # Mock all the diagram modules
        mock_diagrams = MagicMock()
        mock_aws_management = MagicMock()
        mock_aws_security = MagicMock()
        mock_aws_storage = MagicMock()
        
        # Setup context manager for Diagram
        mock_diagram_context = MagicMock()
        mock_diagrams.Diagram.return_value.__enter__ = Mock(return_value=mock_diagram_context)
        mock_diagrams.Diagram.return_value.__exit__ = Mock(return_value=None)
        
        # Mock sys.modules to simulate installed packages
        with patch.dict('sys.modules', {
            'diagrams': mock_diagrams,
            'diagrams.aws': MagicMock(),
            'diagrams.aws.management': mock_aws_management,
            'diagrams.aws.security': mock_aws_security,
            'diagrams.aws.storage': mock_aws_storage
        }):
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                result_path = diagram_generator.generate_control_tower_architecture(output_dir)
                
                assert result_path == output_dir / "control_tower_architecture.png"
                mock_diagrams.Diagram.assert_called_once()
    
    def test_generate_control_tower_architecture_import_error(self, diagram_generator):
        """Test Control Tower architecture generation with import error."""
        # Ensure diagrams is not in sys.modules
        with patch.dict('sys.modules', {}, clear=True):
            with pytest.raises(DiagramGenerationError, match="diagrams package not installed"):
                diagram_generator.generate_control_tower_architecture()
    
    def test_generate_control_tower_architecture_error(self, diagram_generator):
        """Test Control Tower architecture generation with general error."""
        mock_diagrams = MagicMock()
        mock_diagrams.Diagram.side_effect = Exception("Diagram error")
        
        with patch.dict('sys.modules', {
            'diagrams': mock_diagrams,
            'diagrams.aws': MagicMock(),
            'diagrams.aws.management': MagicMock(),
            'diagrams.aws.security': MagicMock(),
            'diagrams.aws.storage': MagicMock()
        }):
            with pytest.raises(DiagramGenerationError, match="Failed to generate Control Tower architecture"):
                diagram_generator.generate_control_tower_architecture()
    
    def test_generate_security_topology_success(self, diagram_generator):
        """Test successful security topology diagram generation."""
        mock_diagrams = MagicMock()
        mock_aws_security = MagicMock()
        mock_aws_management = MagicMock()
        
        mock_diagram_context = MagicMock()
        mock_diagrams.Diagram.return_value.__enter__ = Mock(return_value=mock_diagram_context)
        mock_diagrams.Diagram.return_value.__exit__ = Mock(return_value=None)
        
        with patch.dict('sys.modules', {
            'diagrams': mock_diagrams,
            'diagrams.aws': MagicMock(),
            'diagrams.aws.security': mock_aws_security,
            'diagrams.aws.management': mock_aws_management
        }):
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                result_path = diagram_generator.generate_security_topology(output_dir)
                
                assert result_path == output_dir / "security_topology.png"
                mock_diagrams.Diagram.assert_called_once()
    
    def test_generate_security_topology_import_error(self, diagram_generator):
        """Test security topology generation with import error."""
        with patch.dict('sys.modules', {}, clear=True):
            with pytest.raises(DiagramGenerationError, match="diagrams package not installed"):
                diagram_generator.generate_security_topology()
    
    def test_generate_organization_structure_success(self, diagram_generator):
        """Test successful organization structure diagram generation."""
        mock_diagrams = MagicMock()
        mock_aws_management = MagicMock()
        mock_aws_general = MagicMock()
        
        mock_diagram_context = MagicMock()
        mock_diagrams.Diagram.return_value.__enter__ = Mock(return_value=mock_diagram_context)
        mock_diagrams.Diagram.return_value.__exit__ = Mock(return_value=None)
        
        with patch.dict('sys.modules', {
            'diagrams': mock_diagrams,
            'diagrams.aws': MagicMock(),
            'diagrams.aws.management': mock_aws_management,
            'diagrams.aws.general': mock_aws_general
        }):
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                result_path = diagram_generator.generate_organization_structure(output_dir)
                
                assert result_path == output_dir / "organization_structure.png"
                mock_diagrams.Diagram.assert_called_once()
    
    def test_generate_organization_structure_error(self, diagram_generator):
        """Test organization structure generation with error."""
        mock_diagrams = MagicMock()
        mock_diagrams.Diagram.side_effect = Exception("Structure error")
        
        with patch.dict('sys.modules', {
            'diagrams': mock_diagrams,
            'diagrams.aws': MagicMock(),
            'diagrams.aws.management': MagicMock(),
            'diagrams.aws.general': MagicMock()
        }):
            with pytest.raises(DiagramGenerationError, match="Failed to generate organization structure"):
                diagram_generator.generate_organization_structure()
    
    def test_generate_all_diagrams_success(self, diagram_generator):
        """Test successful generation of all diagrams."""
        with patch.object(diagram_generator, 'generate_control_tower_architecture') as mock_ct, \
             patch.object(diagram_generator, 'generate_security_topology') as mock_security, \
             patch.object(diagram_generator, 'generate_organization_structure') as mock_org:
            
            mock_ct.return_value = Path("ct.png")
            mock_security.return_value = Path("security.png")
            mock_org.return_value = Path("org.png")
            
            result = diagram_generator.generate_all_diagrams()
            
            assert len(result) == 3
            assert Path("ct.png") in result
            assert Path("security.png") in result
            assert Path("org.png") in result
            
            mock_ct.assert_called_once()
            mock_security.assert_called_once()
            mock_org.assert_called_once()
    
    def test_generate_all_diagrams_error(self, diagram_generator):
        """Test generation of all diagrams with error."""
        with patch.object(diagram_generator, 'generate_control_tower_architecture', side_effect=Exception("CT error")):
            with pytest.raises(DiagramGenerationError, match="Failed to generate all diagrams"):
                diagram_generator.generate_all_diagrams()
    
    def test_default_output_directory(self, diagram_generator):
        """Test that default output directory is used when none provided."""
        mock_diagrams = MagicMock()
        mock_diagram_context = MagicMock()
        mock_diagrams.Diagram.return_value.__enter__ = Mock(return_value=mock_diagram_context)
        mock_diagrams.Diagram.return_value.__exit__ = Mock(return_value=None)
        
        with patch.dict('sys.modules', {
            'diagrams': mock_diagrams,
            'diagrams.aws': MagicMock(),
            'diagrams.aws.management': MagicMock(),
            'diagrams.aws.security': MagicMock(),
            'diagrams.aws.storage': MagicMock()
        }), patch('pathlib.Path.mkdir') as mock_mkdir:
            
            result_path = diagram_generator.generate_control_tower_architecture()
            
            # Should use default docs/ directory
            assert str(result_path) == "docs/control_tower_architecture.png"
            mock_mkdir.assert_called_once_with(exist_ok=True)
