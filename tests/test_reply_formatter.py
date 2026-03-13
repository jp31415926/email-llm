#!/usr/bin/env python3
"""Tests for the reply_formatter module."""

import pytest

from reply_formatter import extract_latest_user_message


class TestExtractLatestUserMessage:
    """Tests for extract_latest_user_message function."""

    def test_no_separator_returns_body(self):
        """Plain email with no 'On ... wrote:' separator is returned as-is (stripped)."""
        body = "Hello, I have a question about your service.\n\nPlease advise."
        assert extract_latest_user_message(body) == body

    def test_returns_text_before_separator(self):
        """Only the text before the separator is returned."""
        body = (
            "This is my new reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Previous bot message.\n"
        )
        result = extract_latest_user_message(body)
        assert result == "This is my new reply."
        assert "Previous bot message." not in result
        assert "wrote:" not in result

    def test_separator_line_not_in_result(self):
        """The 'On ... wrote:' line is not in the result."""
        body = (
            "User reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Quoted content.\n"
        )
        result = extract_latest_user_message(body)
        assert "On Wed, Mar 4, 2026" not in result
        assert "wrote:" not in result

    def test_quoted_content_not_in_result(self):
        """Quoted content after the separator is excluded."""
        body = (
            "New message.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Line one.\n"
            "> Line two.\n"
        )
        result = extract_latest_user_message(body)
        assert "Line one." not in result
        assert "Line two." not in result
        assert result == "New message."

    def test_two_line_wrapped_separator(self):
        """Separator split across two lines is correctly detected."""
        body = (
            "User reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 PM Some Name <\n"
            "bot@example.com> wrote:\n"
            "\n"
            "> Quoted text.\n"
        )
        result = extract_latest_user_message(body)
        assert result == "User reply."
        assert "Quoted text." not in result
        assert "wrote:" not in result

    def test_no_text_before_separator_returns_empty(self):
        """If there is no text before the separator, returns empty string."""
        body = (
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Quoted only.\n"
        )
        result = extract_latest_user_message(body)
        assert result == ""

    def test_empty_body(self):
        """Empty body returns empty string."""
        assert extract_latest_user_message("") == ""

    def test_multiline_reply_preserved(self):
        """Multi-line user reply is returned intact."""
        body = (
            "Line one of reply.\n"
            "Line two of reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Previous.\n"
        )
        result = extract_latest_user_message(body)
        assert "Line one of reply." in result
        assert "Line two of reply." in result
        assert "Previous." not in result

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped from the result."""
        body = "  \n  My message.  \n\nOn some date wrote:\n\n> old\n"
        result = extract_latest_user_message(body)
        assert result == "My message."
