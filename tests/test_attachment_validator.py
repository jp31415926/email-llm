#!/usr/bin/env python3
"""Tests for attachment_validator module."""

import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import attachment_validator


def test_no_attachments():
    """Test email with no attachments doesn't raise exception."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'
    msg.attach(MIMEText('Body text', 'plain'))

    # Should not raise any exception
    attachment_validator.raise_if_unsupported(msg, ['.txt', '.md'])


def test_all_allowed():
    """Test email with only allowed extensions doesn't raise exception."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    msg.attach(MIMEText('Text file content', 'plain'))
    msg.attach(MIMEText('Markdown content', 'plain'))

    # Set filenames for attachments
    for part in msg.walk():
        if not part.is_multipart():
            part.add_header('Content-Disposition', 'attachment', filename='file.txt')

    # Add another attachment with .md extension
    msg.attach(MIMEText('# Markdown', 'plain'))
    for part in msg.walk():
        if not part.is_multipart():
            if part.get_filename() is None:
                part.add_header('Content-Disposition', 'attachment', filename='document.md')

    # Should not raise exception
    attachment_validator.raise_if_unsupported(msg, ['.txt', '.md'])


def test_one_unsupported():
    """Test email with one unsupported extension raises exception."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    # Add allowed attachment
    msg.attach(MIMEText('Text content', 'plain'))
    for part in msg.walk():
        if not part.is_multipart():
            if part.get_filename() is None:
                part.add_header('Content-Disposition', 'attachment', filename='allowed.txt')

    # Add unsupported attachment
    msg.attach(MIMEText('Executable content', 'plain'))
    for part in msg.walk():
        if not part.is_multipart():
            if part.get_filename() is None:
                part.add_header('Content-Disposition', 'attachment', filename='malware.exe')

    # Should raise exception with .exe in disallowed list
    try:
        attachment_validator.raise_if_unsupported(msg, ['.txt', '.md'])
        assert False, "Expected UnsupportedAttachmentError"
    except attachment_validator.UnsupportedAttachmentError as e:
        assert 'malware.exe' in e.disallowed_names
        assert '.exe' in str(e)


def test_case_insensitive():
    """Test extension check is case-insensitive."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    # Add attachment with uppercase extension
    msg.attach(MIMEText('Content', 'plain'))
    for part in msg.walk():
        if not part.is_multipart():
            if part.get_filename() is None:
                part.add_header('Content-Disposition', 'attachment', filename='FILE.TXT')

    # .TXT should be allowed when .txt is in allowed list
    attachment_validator.raise_if_unsupported(msg, ['.txt', '.md'])

    # Now test with unsupported uppercase extension
    msg2 = MIMEMultipart()
    msg2['From'] = 'test@example.com'
    msg2['Subject'] = 'Test'

    msg2.attach(MIMEText('Content', 'plain'))
    for part in msg2.walk():
        if not part.is_multipart():
            if part.get_filename() is None:
                part.add_header('Content-Disposition', 'attachment', filename='program.EXE')

    try:
        attachment_validator.raise_if_unsupported(msg2, ['.txt', '.md'])
        assert False, "Expected UnsupportedAttachmentError"
    except attachment_validator.UnsupportedAttachmentError as e:
        assert 'program.EXE' in e.disallowed_names


def test_empty_allowed_list():
    """Test with empty allowed extensions list - any extension should raise."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    msg.attach(MIMEText('Content', 'plain'))
    for part in msg.walk():
        if not part.is_multipart():
            if part.get_filename() is None:
                part.add_header('Content-Disposition', 'attachment', filename='file.txt')

    # With empty allowed list, even .txt should raise
    try:
        attachment_validator.raise_if_unsupported(msg, [])
        assert False, "Expected UnsupportedAttachmentError"
    except attachment_validator.UnsupportedAttachmentError as e:
        assert 'file.txt' in e.disallowed_names


def test_mixed_allowed_and_unsupported():
    """Test email with mix of allowed and unsupported attachments."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    # Add multiple attachments
    for i, (ext, content) in enumerate([
        ('.txt', 'Text file'),
        ('.exe', 'Executable'),
        ('.md', 'Markdown'),
        ('.dll', 'DLL')
    ]):
        msg.attach(MIMEText(content, 'plain'))
        for part in msg.walk():
            if not part.is_multipart():
                if part.get_filename() is None:
                    part.add_header('Content-Disposition', 'attachment', filename=f'file{i}{ext}')

    # Should raise with both .exe and .dll
    try:
        attachment_validator.raise_if_unsupported(msg, ['.txt', '.md'])
        assert False, "Expected UnsupportedAttachmentError"
    except attachment_validator.UnsupportedAttachmentError as e:
        disallowed = e.disallowed_names
        # Check that both unsupported files are in the list
        assert any('exe' in f.lower() for f in disallowed)
        assert any('dll' in f.lower() for f in disallowed)
        # Check that allowed files are not in the list
        assert not any('txt' in f.lower() for f in disallowed)
        assert not any('md' in f.lower() for f in disallowed)


def test_no_filename():
    """Test email part without filename is skipped."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    # Create attachment without filename
    msg.attach(MIMEText('Content', 'plain'))
    for part in msg.walk():
        if not part.is_multipart():
            part.add_header('Content-Disposition', 'attachment')

    # Should not raise since no filename is present
    attachment_validator.raise_if_unsupported(msg, ['.txt'])


def test_non_attachment_parts():
    """Test that non-attachment parts are skipped."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    # Add text part (not an attachment)
    msg.attach(MIMEText('Body', 'plain'))

    # Add attachment with unsupported extension
    msg.attach(MIMEText('Content', 'plain'))
    for part in msg.walk():
        if not part.is_multipart():
            if part.get_filename() is None:
                part.add_header('Content-Disposition', 'attachment', filename='file.exe')

    # Should raise only for the attachment, not the body
    try:
        attachment_validator.raise_if_unsupported(msg, ['.txt'])
        assert False, "Expected UnsupportedAttachmentError"
    except attachment_validator.UnsupportedAttachmentError as e:
        assert 'file.exe' in e.disallowed_names


def test_read_txt_md_attachments():
    """Test reading .txt and .md attachments returns both."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    # Add .txt attachment
    txt_part = MIMEText('This is a text file', 'plain')
    txt_part.add_header('Content-Disposition', 'attachment', filename='document.txt')
    msg.attach(txt_part)

    # Add .md attachment
    md_part = MIMEText('# Markdown Content', 'plain')
    md_part.add_header('Content-Disposition', 'attachment', filename='readme.md')
    msg.attach(md_part)

    allowed = attachment_validator.read_allowed_attachments(msg, ['.txt', '.md'])
    
    assert len(allowed) == 2
    contents = {name: content for name, content in allowed}
    assert 'document.txt' in contents
    assert 'readme.md' in contents
    assert contents['document.txt'] == 'This is a text file'
    assert contents['readme.md'] == '# Markdown Content'


def test_skip_disallowed():
    """Test that disallowed extensions (.exe) are skipped."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    # Add allowed .txt attachment
    txt_part = MIMEText('This is allowed', 'plain')
    txt_part.add_header('Content-Disposition', 'attachment', filename='allowed.txt')
    msg.attach(txt_part)

    # Add disallowed .exe attachment
    exe_part = MIMEText('This is not allowed', 'plain')
    exe_part.add_header('Content-Disposition', 'attachment', filename='malware.exe')
    msg.attach(exe_part)

    allowed = attachment_validator.read_allowed_attachments(msg, ['.txt', '.md'])
    
    assert len(allowed) == 1
    filename, content = allowed[0]
    assert filename == 'allowed.txt'
    assert content == 'This is allowed'


def test_utf8_fallback():
    """Test UTF-8 fallback to ISO-8859-1 when UTF-8 decode fails."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    # Create bytes that are valid ISO-8859-1 but not valid UTF-8
    # Use a high-byte character that exists in ISO-8859-1 but not UTF-8
    iso_bytes = b'\xe9=utf-8 invalid \xe0'
    
    text_part = MIMEText('', 'plain')
    text_part.set_payload(iso_bytes)
    text_part.add_header('Content-Disposition', 'attachment', filename='special.txt')
    msg.attach(text_part)

    allowed = attachment_validator.read_allowed_attachments(msg, ['.txt'])
    
    assert len(allowed) == 1
    filename, content = allowed[0]
    assert filename == 'special.txt'
    # Should decode using ISO-8859-1
    assert 'é' in content or '\xe9' in content


def test_read_content_correct():
    """Test that content matches file content exactly."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    expected_content = 'This is the exact content with\nmultiple lines\nand special chars: !@#$%'
    
    text_part = MIMEText(expected_content, 'plain')
    text_part.add_header('Content-Disposition', 'attachment', filename='exact.txt')
    msg.attach(text_part)

    allowed = attachment_validator.read_allowed_attachments(msg, ['.txt'])
    
    assert len(allowed) == 1
    filename, content = allowed[0]
    assert filename == 'exact.txt'
    assert content == expected_content


def test_filename_case_preserved():
    """Test that original filename case is preserved."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    text_part = MIMEText('Content', 'plain')
    text_part.add_header('Content-Disposition', 'attachment', filename='MyDocument.TXT')
    msg.attach(text_part)

    allowed = attachment_validator.read_allowed_attachments(msg, ['.txt'])
    
    assert len(allowed) == 1
    filename, content = allowed[0]
    # Original case should be preserved
    assert filename == 'MyDocument.TXT'


def test_no_attachments_read():
    """Test empty email returns empty list."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'
    msg.attach(MIMEText('Body', 'plain'))

    allowed = attachment_validator.read_allowed_attachments(msg, ['.txt', '.md'])
    
    assert allowed == []


def test_empty_allowed_list_read():
    """Test with empty allowed list returns empty result."""
    msg = MIMEMultipart()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test'

    text_part = MIMEText('Content', 'plain')
    text_part.add_header('Content-Disposition', 'attachment', filename='file.txt')
    msg.attach(text_part)

    allowed = attachment_validator.read_allowed_attachments(msg, [])
    
    assert allowed == []


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
