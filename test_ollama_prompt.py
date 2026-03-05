#!/usr/bin/env python3
"""Tests for ollama_prompt module."""

import logging
import pytest

from ollama_prompt import compose_ollama_prompt


# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestComposeOllamaPrompt:
    """Test suite for compose_ollama_prompt function."""

    def test_with_prefix_and_body(self) -> None:
        """Test prompt with prefix and body returns correct format."""
        config = {
            'ollama_prefix_prompt': 'You are a helpful email assistant.',
        }
        attachments = []
        body = 'Hello, I need help with my order.'

        result = compose_ollama_prompt(config, attachments, body)

        assert 'You are a helpful email assistant.' in result
        assert 'Hello, I need help with my order.' in result

    def test_with_attachments_only(self) -> None:
        """Test prompt with attachments but no body omits email_body tag."""
        config = {
            'ollama_prefix_prompt': 'You are a helpful email assistant.',
        }
        attachments = [
            ('notes.txt', 'Some important notes'),
            ('readme.md', '# Project README'),
        ]
        body = ''

        result = compose_ollama_prompt(config, attachments, body)

        assert 'You are a helpful email assistant.' in result
        assert '<attachment filename="notes.txt">Some important notes</attachment>' in result
        assert '<attachment filename="readme.md"># Project README</attachment>' in result
        # Should NOT contain email_body tag
        assert '<email_body>' not in result

    def test_empty_inputs(self) -> None:
        """Test with blank prefix, no attachments, no body returns empty string."""
        config = {
            'ollama_prefix_prompt': '',
        }
        attachments = []
        body = ''

        result = compose_ollama_prompt(config, attachments, body)

        assert result == ''

    def test_multiple_attachments(self) -> None:
        """Test with multiple attachments returns correct ordering and tags."""
        config = {
            'ollama_prefix_prompt': '',
        }
        attachments = [
            ('first.txt', 'Content of first'),
            ('second.txt', 'Content of second'),
            ('third.txt', 'Content of third'),
        ]
        body = ''

        result = compose_ollama_prompt(config, attachments, body)

        # Check all attachments are present in order
        assert '<attachment filename="first.txt">Content of first</attachment>' in result
        assert '<attachment filename="second.txt">Content of second</attachment>' in result
        assert '<attachment filename="third.txt">Content of third</attachment>' in result

    def test_preserves_newlines_in_body(self) -> None:
        """Test that body with newlines preserves them (not escaped)."""
        config = {
            'ollama_prefix_prompt': '',
        }
        attachments = []
        body = 'Line 1\nLine 2\nLine 3'

        result = compose_ollama_prompt(config, attachments, body)

        assert 'Line 1\nLine 2\nLine 3' in result

    def test_prefix_only_no_attachments_no_body(self) -> None:
        """Test with prefix only, no attachments, no body."""
        config = {
            'ollama_prefix_prompt': 'You are a helpful assistant.',
        }
        attachments = []
        body = ''

        result = compose_ollama_prompt(config, attachments, body)

        assert result == 'You are a helpful assistant.'

    def test_attachments_without_prefix(self) -> None:
        """Test with attachments but no prefix prompt."""
        config = {
            'ollama_prefix_prompt': '',
        }
        attachments = [
            ('data.txt', 'Data content'),
        ]
        body = 'Email content here'

        result = compose_ollama_prompt(config, attachments, body)

        assert '<attachment filename="data.txt">Data content</attachment>' in result
        assert 'Email content here' in result

    def test_attachment_with_special_chars_in_content(self) -> None:
        """Test that special characters in attachment content are preserved."""
        config = {
            'ollama_prefix_prompt': '',
        }
        attachments = [
            ('file.txt', 'Content with <tags> and & symbols'),
        ]
        body = ''

        result = compose_ollama_prompt(config, attachments, body)

        # Per spec: do NOT escape XML special chars - LLM expects raw body
        assert '<attachment filename="file.txt">Content with <tags> and & symbols</attachment>' in result

    def test_comma_in_filename(self) -> None:
        """Test filename with comma in the name."""
        config = {
            'ollama_prefix_prompt': '',
        }
        attachments = [
            ('file,with,commas.txt', 'Content'),
        ]
        body = ''

        result = compose_ollama_prompt(config, attachments, body)

        assert '<attachment filename="file,with,commas.txt">Content</attachment>' in result
