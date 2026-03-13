#!/usr/bin/env python3
"""Tests for email_parser module."""

import logging
import tempfile
from email import message_from_string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import email_parser


def test_parse_email_with_plain_text():
    """Test parsing email with plain text body."""
    # Create a simple email with plain text body
    msg = MIMEMultipart()
    msg['From'] = 'John Doe <john@example.com>'
    msg['Subject'] = 'Test Subject'
    msg['Message-Id'] = '<msg123@example.com>'
    msg['References'] = '<ref1@example.com>'
    msg['In-Reply-To'] = '<reply1@example.com>'

    msg.attach(MIMEText('This is the plain text body.', 'plain'))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.eml', delete=False) as f:
        f.write(msg.as_string())
        f.flush()
        path = Path(f.name)

    try:
        result = email_parser.parse_email(path)

        assert result['from'] == 'john@example.com', f"Expected 'john@example.com', got '{result['from']}'"
        assert result['subject'] == 'Test Subject'
        assert result['body'] == 'This is the plain text body.'
        assert result['message_id'] == '<msg123@example.com>'
        assert result['references'] == '<ref1@example.com>'
        assert result['in_reply_to'] == '<reply1@example.com>'
    finally:
        path.unlink()


def test_parse_email_html_fallback():
    """Test parsing email with HTML body (fallback case)."""
    # Create email with only HTML body
    msg = MIMEMultipart()
    msg['From'] = 'Jane Smith <jane@example.com>'
    msg['Subject'] = 'HTML Email'
    msg['Message-Id'] = '<htmlmsg456@example.com>'

    html_content = '<html><body><p>This is <b>HTML</b> content.</p></body></html>'
    msg.attach(MIMEText(html_content, 'html'))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.eml', delete=False) as f:
        f.write(msg.as_string())
        f.flush()
        path = Path(f.name)

    try:
        result = email_parser.parse_email(path)

        assert result['from'] == 'jane@example.com'
        assert result['subject'] == 'HTML Email'
        assert 'HTML' in result['body']
        assert '<b>' not in result['body']  # HTML tags should be stripped
        assert result['message_id'] == '<htmlmsg456@example.com>'
    finally:
        path.unlink()


def test_parse_email_empty_body():
    """Test parsing email with multipart but no text content."""
    # Create email with no text parts
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'No Body'

    # Attach something that's not text
    msg.attach(MIMEText('', 'html'))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.eml', delete=False) as f:
        f.write(msg.as_string())
        f.flush()
        path = Path(f.name)

    try:
        result = email_parser.parse_email(path)

        assert result['from'] == 'test@example.com'
        assert result['body'] == ''  # Empty body when no text content
    finally:
        path.unlink()


def test_parse_email_malformed(caplog):
    """Test parsing email that causes a decoding error."""
    # Create an email with valid structure but problematic content that causes errors
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.eml', delete=False) as f:
        # Write valid email header but binary body that can't be decoded properly
        # This will work with BytesParser but get_content() may fail
        f.write(b'From: test@example.com\r\n')
        f.write(b'Subject: Test\r\n')
        f.write(b'Content-Type: text/plain; charset=utf-8\r\n')
        f.write(b'\r\n')
        # Binary content that might cause encoding issues
        f.write(b'\xff\xfe')  # BOM in wrong place
        f.flush()
        path = Path(f.name)

    try:
        with caplog.at_level(logging.WARNING):
            result = email_parser.parse_email(path)

        # The parser should handle this gracefully
        assert result['from'] == 'test@example.com'
        assert result['subject'] == 'Test'
        # Body may or may not be empty depending on how the parser handles it
        # The key is it doesn't crash
    finally:
        path.unlink()


def test_parse_email_from_subject_cleaned():
    """Test that From header is cleaned using parseaddr."""
    # Test with display name
    msg = MIMEMultipart()
    msg['From'] = 'John Doe <john.doe@example.com>'
    msg['Subject'] = 'Subject Line'
    msg.attach(MIMEText('Body text', 'plain'))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.eml', delete=False) as f:
        f.write(msg.as_string())
        f.flush()
        path = Path(f.name)

    try:
        result = email_parser.parse_email(path)

        assert result['from'] == 'john.doe@example.com', f"Expected 'john.doe@example.com', got '{result['from']}'"
        assert result['subject'] == 'Subject Line'
    finally:
        path.unlink()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
