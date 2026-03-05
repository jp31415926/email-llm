# AGENTS.md

## Files
`spec.md` - Project specification
`blueprint.md` - Project blueprint and prompts
`prompts.md` - Prompts for the developer sub-agent

## Code Style Guidelines

### General
- Use Python 3.11+
- Strict UTF-8 encoding for all files
- All scripts must have shebangs (`#!/usr/bin/env python3`)
- Use the `logging` module for all output instead of `print()`
- All code must be executable and follow the specification exactly

### Imports
- Use standard library modules where possible: `sys`, `os`, `email`, `tempfile`, `logging`, `subprocess`, `argparse`
- Import modules at the top of each file in standard order:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- Import individual modules rather than using wildcard imports: `from email import message_from_file` instead of `from email import *`

### Test Commands
- `python3 -m pytest tests/` - Run all unit and integration tests
- `python3 -m pytest tests/ -v` - Run tests with verbose output
- `python3 -m pytest tests/ -k "test_"` - Run tests matching pattern "test_" 

For running a single test:
- `python3 -m pytest tests/test_default_extractor.py::test_valid_plain_text -v`

### Formatting
- Indentation: 2 spaces (no tabs)
- Line length: Maximum 88 characters (PEP8 + black)
- No trailing whitespace
- Use snake_case for variables and functions
- Use PascalCase for classes
- Single blank lines to separate logical sections of code
- Double blank lines to separate top-level function or class definitions

### Naming Conventions
- Variables: `snake_case` (e.g., `email_message`, `output_dir`)
- Constants: `UPPER_CASE` (e.g., `MAX_RETRIES`)
- Functions: `snake_case` (e.g., `parse_email`, `extract_joke`)
- Classes: `PascalCase` (e.g., `EmailExtractor`)
- Private methods: `_snake_case` (e.g., `_validate_headers`)

### Error Handling
- Handle all exceptions gracefully

### File Handling
- All email files must be processed with ISO-8859-1 encoding
