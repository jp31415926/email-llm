#!/usr/bin/env python3
"""Reformats email reply bodies into chronological chat format.

When a user replies to a bot email, the body looks like:

    User's new reply text...

    On Wed, Mar 4, 2026, 3:45 PM <bot@example.com> wrote:

    > Previous conversation content...

This module detects the 'On ... wrote:' separator, strips quote characters,
reflows the quoted text, and reassembles it in oldest-first (chat) order:

    Previous conversation content...

    User's new reply text...
"""

import re
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


def _strip_quotes(lines: list[str]) -> list[str]:
    """Remove leading '>' quote characters from each line."""
    return [re.sub(r'^(>\s?)+', '', line) for line in lines]


def _reflow(lines: list[str]) -> list[str]:
    """Join consecutive non-blank lines into single long lines.

    Blank lines are preserved as paragraph separators. Consecutive
    non-blank lines within a paragraph are joined with a space.
    """
    result: list[str] = []
    current_para: list[str] = []

    for line in lines:
        if line.strip() == '':
            if current_para:
                result.append(' '.join(current_para))
                current_para = []
            result.append('')
        else:
            current_para.append(line.strip())

    if current_para:
        result.append(' '.join(current_para))

    return result


def reformat_reply_body(body: str) -> str:
    """Reformat an email reply body into chronological chat format.

    Detects the 'On ... wrote:' separator. If found:
    - Splits into user_reply (before separator) and quoted_body (after)
    - Strips '>' quote characters from quoted_body
    - Reflows quoted_body to join wrapped lines into paragraphs
    - Returns quoted_body followed by user_reply (oldest message first)

    Returns body unchanged if no separator is found.
    """
    lines = body.split('\n')
    sep = _find_separator(lines)
    if sep is None:
        return body

    sep_start, sep_end = sep

    user_reply_lines = lines[:sep_start]
    quoted_lines = lines[sep_end:]

    # Strip quote characters then reflow the quoted section
    quoted_lines = _strip_quotes(quoted_lines)
    quoted_lines = _reflow(quoted_lines)

    user_reply = '\n'.join(user_reply_lines).strip()
    quoted_body = '\n'.join(quoted_lines).strip()

    if user_reply:
        return f"{quoted_body}\n\n{user_reply}"
    return quoted_body
