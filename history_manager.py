#!/usr/bin/env python3
"""Manages per-thread conversation history for the email bot."""

import re
from datetime import date
from pathlib import Path
from typing import Tuple


def get_thread_root_id(headers: dict) -> str:
    """Get the root message ID for a thread.

    Uses References[0] if present, else In-Reply-To, else Message-Id.
    Strips angle brackets.
    """
    references = headers.get('references', '').strip()
    if references:
        root = references.split()[0]
    else:
        root = headers.get('in_reply_to', '').strip() or headers.get('message_id', '').strip()
    return root.strip('<>')


def get_history_paths(headers: dict, config: dict) -> Tuple[Path, Path]:
    """Get paths for the history and compact files for a thread.

    Filename: {sanitized_subject}__{sanitized_root_id}.txt
    """
    subject = headers.get('subject', '').lower()
    subject = re.sub(r'\W+', '_', subject).strip('_')[:50]

    root_id = get_thread_root_id(headers)
    root_id = re.sub(r'\W+', '_', root_id).strip('_')

    history_folder = Path(config.get('history_folder', 'history'))
    base_name = f"{subject}__{root_id}"
    history_path = history_folder / f"{base_name}.txt"
    compact_path = history_folder / f"{base_name}-compact.txt"
    return history_path, compact_path


def get_recent_history(history_path: Path) -> str:
    """Get the recent (uncompacted) turns from a history file.

    Returns everything after the last '=== COMPACTED:' marker, or the
    whole file if no marker exists. Returns empty string if file missing.
    """
    if not history_path.exists():
        return ""
    content = history_path.read_text(encoding='utf-8')
    last_marker = content.rfind('\n=== COMPACTED:')
    if last_marker == -1:
        return content.strip()
    # Skip past the marker line
    after_marker = content[last_marker:]
    newline_after = after_marker.find('\n', 1)
    if newline_after == -1:
        return ""
    return after_marker[newline_after:].strip()


def build_prompt_history(history_path: Path, compact_path: Path) -> str:
    """Build the history string to include in the LLM prompt.

    Returns:
        Combined compact summary and recent turns, or empty string if none.
    """
    compact_text = ""
    if compact_path.exists():
        compact_text = compact_path.read_text(encoding='utf-8').strip()

    recent = get_recent_history(history_path)

    if compact_text and recent:
        return f"[Conversation summary]\n{compact_text}\n\n[Recent conversation]\n{recent}"
    elif compact_text:
        return f"[Conversation summary]\n{compact_text}"
    elif recent:
        return recent
    return ""


def estimate_prompt_size(compact_path: Path, history_path: Path, new_message: str) -> int:
    """Estimate the total prompt context size in characters."""
    return len(build_prompt_history(history_path, compact_path)) + len(new_message)


def append_turn(history_path: Path, user_message: str, assistant_response: str) -> None:
    """Append a User/Assistant turn to the history file."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    turn = f"User:\n{user_message}\n\nAssistant:\n{assistant_response}"
    if not history_path.exists() or history_path.stat().st_size == 0:
        history_path.write_text(turn, encoding='utf-8')
    else:
        with history_path.open('a', encoding='utf-8') as f:
            f.write(f"\n\n{turn}")


def compact_history(history_path: Path, compact_path: Path, config: dict) -> str:
    """Compact conversation history using the LLM.

    Returns the new compact summary text.
    """
    from ollama_client import call_ollama
    from llamacpp_client import call_llamacpp

    existing_compact = ""
    if compact_path.exists():
        existing_compact = compact_path.read_text(encoding='utf-8').strip()

    recent = get_recent_history(history_path)

    parts = [
        "Summarize the following conversation concisely, preserving all key facts, "
        "decisions, and context the assistant needs to continue helpfully:"
    ]
    if existing_compact:
        parts.append(existing_compact)
    if recent:
        parts.append(recent)
    summarize_prompt = "\n\n".join(parts)

    backend = config.get('llm_backend', 'ollama')
    if backend == 'llamacpp':
        new_compact = call_llamacpp(summarize_prompt, config)
    else:
        new_compact = call_ollama(summarize_prompt, config)

    new_compact = new_compact.strip()

    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(new_compact, encoding='utf-8')

    today = date.today().strftime('%Y-%m-%d')
    with history_path.open('a', encoding='utf-8') as f:
        f.write(f"\n\n=== COMPACTED: {today} ===")

    return new_compact


def needs_post_reply_compact(history_path: Path, config: dict) -> bool:
    """Check if post-reply auto-compaction is needed."""
    threshold = config.get('history_compact_threshold_chars', 40000)
    return len(get_recent_history(history_path)) > threshold


def needs_pre_reply_compact(history_path: Path, compact_path: Path, new_message: str, config: dict) -> bool:
    """Check if pre-reply forced compaction is needed."""
    max_chars = config.get('history_max_prompt_chars', 60000)
    return estimate_prompt_size(compact_path, history_path, new_message) > max_chars
