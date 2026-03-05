#!/usr/bin/env python3
"""Ollama prompt builder module for constructing XML-wrapped prompts."""

from typing import List, Tuple


def compose_ollama_prompt(config: dict, attachments: List[Tuple[str, str]], body: str) -> str:
    """Build XML-wrapped prompt for Ollama.

    Args:
        config: Configuration dictionary containing ollama_prefix_prompt.
        attachments: List of (filename, content) tuples for allowed attachments.
        body: The email body content to include.

    Returns:
        A formatted string prompt with XML tags for attachments and body.
    """
    prompt_parts: List[str] = []

    # Add prefix prompt if non-empty
    prefix_prompt = config.get('ollama_prefix_prompt', '')
    if prefix_prompt:
        prompt_parts.append(prefix_prompt)

    # Add each attachment with XML tags
    for filename, content in attachments:
        prompt_parts.append(f'<attachment filename="{filename}">{content}</attachment>')

    # Add email body if non-empty
    if body:
        prompt_parts.append(f'<email_body>{body}</email_body>')

    # Join all parts with double newlines for separation
    return '\n\n'.join(prompt_parts)
