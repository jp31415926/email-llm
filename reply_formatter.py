#!/usr/bin/env python3
"""Extracts the latest user message from an email body.

When a user replies to a bot email, the body looks like:

    User's new reply text...

    On Wed, Mar 4, 2026, 3:45 PM <bot@example.com> wrote:

    > Previous conversation content...

This module detects the 'On ... wrote:' separator and returns only
the text before it (the user's latest message).
"""

from typing import Optional


def _find_separator(lines: list[str]) -> Optional[tuple[int, int]]:
    """Find the line indices (start, end exclusive) of the 'On ... wrote:' separator.

    Handles single-line and two-line wrapped variants, e.g.:
        On Wed, Mar 4, 2026, 3:45 PM <bot@example.com> wrote:
    or:
        On Wed, Mar 4, 2026, 3:45 PM Some Name <
        bot@example.com> wrote:

    Returns (start_index, end_index) where end_index is the first line
    after the separator, or None if no separator is found.
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith('On '):
            continue
        # Check single-line form
        if stripped.endswith('wrote:'):
            return (i, i + 1)
        # Check two-line wrapped form
        if i + 1 < len(lines):
            combined = stripped + ' ' + lines[i + 1].strip()
            if combined.endswith('wrote:'):
                return (i, i + 2)
    return None


def extract_latest_user_message(body: str) -> str:
    """Extract only the latest user message from an email body.

    If the body contains an 'On ... wrote:' separator, returns only the text
    before it (the user's new reply). Otherwise returns the full body stripped.
    """
    lines = body.split('\n')
    sep = _find_separator(lines)
    if sep is None:
        return body.strip()
    sep_start, _ = sep
    return '\n'.join(lines[:sep_start]).strip()
