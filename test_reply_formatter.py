#!/usr/bin/env python3
"""Tests for the reply_formatter module."""

import pytest

from reply_formatter import reformat_reply_body


class TestReformatReplyBody:
    """Tests for reformat_reply_body function."""

    def test_non_reply_unchanged(self):
        """Plain email with no 'On ... wrote:' separator is returned unchanged."""
        body = "Hello, I have a question about your service.\n\nPlease advise."
        assert reformat_reply_body(body) == body

    def test_basic_reply_reordered(self):
        """User reply moves to end; quoted content comes first."""
        body = (
            "This is my new reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Previous bot message.\n"
        )
        result = reformat_reply_body(body)
        assert result.index("Previous bot message.") < result.index("This is my new reply.")

    def test_separator_line_removed(self):
        """The 'On ... wrote:' line itself is not present in output."""
        body = (
            "User reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Quoted content.\n"
        )
        result = reformat_reply_body(body)
        assert "On Wed, Mar 4, 2026" not in result
        assert "wrote:" not in result

    def test_quote_characters_stripped(self):
        """All leading '>' characters are removed from quoted lines."""
        body = (
            "New message.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Line one.\n"
            "> Line two.\n"
        )
        result = reformat_reply_body(body)
        assert ">" not in result
        assert "Line one." in result
        assert "Line two." in result

    def test_two_line_wrapped_separator(self):
        """Separator split across two lines is correctly identified."""
        body = (
            "User reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 PM Some Name <\n"
            "bot@example.com> wrote:\n"
            "\n"
            "> Quoted text.\n"
        )
        result = reformat_reply_body(body)
        assert "Quoted text." in result
        assert "User reply." in result
        assert result.index("Quoted text.") < result.index("User reply.")
        assert "wrote:" not in result

    def test_blank_lines_preserved(self):
        """Blank lines within the quoted section are preserved."""
        body = (
            "New reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> First paragraph.\n"
            ">\n"
            "> Second paragraph.\n"
        )
        result = reformat_reply_body(body)
        # The blank line between paragraphs should be preserved
        assert "First paragraph." in result
        assert "Second paragraph." in result
        assert "\n\n" in result

    def test_reflowing_joins_wrapped_lines(self):
        """Consecutive non-blank quoted lines are joined into one long line."""
        body = (
            "Reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> This is a long sentence that was\n"
            "> wrapped by the email client.\n"
        )
        result = reformat_reply_body(body)
        # The two wrapped lines should be joined
        assert "This is a long sentence that was wrapped by the email client." in result

    def test_reflowing_preserves_paragraph_break(self):
        """Paragraph break (blank line) in quoted section is not collapsed."""
        body = (
            "Reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Para one line one.\n"
            "> Para one line two.\n"
            ">\n"
            "> Para two.\n"
        )
        result = reformat_reply_body(body)
        assert "Para one line one. Para one line two." in result
        assert "Para two." in result
        # Blank line separates the two paragraphs
        idx_para1 = result.index("Para one line one.")
        idx_blank = result.index("\n\n", idx_para1)
        idx_para2 = result.index("Para two.", idx_blank)
        assert idx_para1 < idx_blank < idx_para2

    def test_no_reply_text_above_separator(self):
        """If there is no text before the separator, returns just the quoted content."""
        body = (
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            "> Quoted only.\n"
        )
        result = reformat_reply_body(body)
        assert "Quoted only." in result
        assert "wrote:" not in result

    def test_empty_body(self):
        """Empty body is returned unchanged."""
        assert reformat_reply_body("") == ""

    def test_multiple_gt_levels_stripped(self):
        """Multiple levels of '>' (e.g. '>> ') are all stripped."""
        body = (
            "Reply.\n"
            "\n"
            "On Wed, Mar 4, 2026, 15:45 <bot@example.com> wrote:\n"
            "\n"
            ">> Doubly quoted.\n"
        )
        result = reformat_reply_body(body)
        assert ">" not in result
        assert "Doubly quoted." in result
