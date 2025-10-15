# Developer Documentation

This directory contains technical documentation for developers working on the AWS Control Tower Automation project.

## For End Users

If you're looking to **use** the tool (not develop it), see the main documentation:
- [Quick Start Guide](../../QUICKSTART.md) - Get started in 5 minutes
- [Configuration Guide](../CONFIGURATION.md) - Configure for your organization
- [Troubleshooting Guide](../TROUBLESHOOTING.md) - Fix common issues
- [Operations Guide](../OPERATIONS.md) - Day-2 operations

## Developer Resources

### Architecture and Design
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Technical architecture details
- Code structure and module organization
- Design patterns and principles
- Integration patterns with AWS services

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd aws-management-automation

# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ --cov=src

# Run linting
flake8 src/
black src/
mypy src/
```

### Code Quality Standards
- **PEP 8 Compliance**: All code must pass flake8 linting
- **Type Hints**: All functions must have complete type annotations
- **Test Coverage**: Minimum 80% test coverage required
- **Documentation**: Comprehensive docstrings following PEP 257

### Testing
- Unit tests in `tests/` directory
- Integration tests for AWS service interactions
- Mock testing for external dependencies
- Coverage reporting with pytest-cov

### Contributing Guidelines
1. Follow project tenets in `notes/tenets.md`
2. All changes must be validated against AWS documentation
3. Security best practices must be maintained
4. Holistic impact assessment required for all changes
5. Code must follow PEP standards and pass all quality checks

### Project Structure
```
src/
├── core/                    # Framework components
├── prerequisites/           # Pre-deployment setup
├── control_tower/          # Control Tower deployment
├── post_deployment/        # Security baseline setup
└── documentation/          # Auto-generated docs
```

### Release Process
1. Update version in setup.py
2. Run full test suite
3. Update CHANGELOG.md
4. Create release tag
5. Update documentation if needed

For detailed technical information, see the files in this directory and the main [ARCHITECTURE.md](../ARCHITECTURE.md) document.
