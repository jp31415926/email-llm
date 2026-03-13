#!/usr/bin/env python3
"""Ollama prompt builder module for constructing XML-wrapped prompts."""

from typing import List, Tuple


def compose_ollama_prompt(config: dict, attachments: List[Tuple[str, str]], body: str, history: str = "") -> str:
    """Build prompt for LLM.

    Args:
        config: Configuration dictionary containing prefix prompt.
        attachments: List of (filename, content) tuples for allowed attachments.
        body: The latest user message to include.
        history: Optional conversation history string to include after prefix.

    Returns:
        A formatted string prompt.
    """
    prompt_parts: List[str] = []

    # Add prefix prompt if non-empty
    backend = config.get('llm_backend', 'ollama')
    prefix_key = 'llamacpp_prefix_prompt' if backend == 'llamacpp' else 'ollama_prefix_prompt'
    prefix_prompt = config.get(prefix_key, '')
    if prefix_prompt:
        prompt_parts.append(prefix_prompt)

    # Add each attachment with XML tags
    for filename, content in attachments:
        prompt_parts.append(f'<attachment filename="{filename}">{content}</attachment>')

    # Add conversation history if present
    if history:
        prompt_parts.append(history)

    # Add latest user message wrapped with User: label
    if body:
        prompt_parts.append(f"User:\n{body}")

    # Join all parts with double newlines for separation
    return '\n\n'.join(prompt_parts)
