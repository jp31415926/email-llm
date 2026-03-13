#!/usr/bin/env python3
"""Command handler for email bot slash commands."""

from pathlib import Path

from history_manager import compact_history


def handle_command(cmd_line: str, headers: dict, history_path: Path, compact_path: Path, config: dict) -> str:
    """Handle a user command and return the reply text.

    Args:
        cmd_line: The full command line (e.g. '/compact').
        headers: Parsed email headers.
        history_path: Path to the thread history file.
        compact_path: Path to the thread compact file.
        config: Configuration dictionary.

    Returns:
        Reply text to send back to the user.
    """
    tokens = cmd_line.strip().split()
    if not tokens:
        return "Unknown command: (empty)"

    cmd = tokens[0].lower()

    if cmd == '/compact':
        new_compact = compact_history(history_path, compact_path, config)
        return new_compact
    else:
        return f"Unknown command: {cmd}"
