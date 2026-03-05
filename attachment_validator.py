#!/usr/bin/env python3
"""Attachment validator module for checking email attachments against allowed extensions."""

import os
from typing import List, Optional, Tuple


class UnsupportedAttachmentError(Exception):
    """Exception raised when an email contains unsupported attachments."""

    def __init__(self, disallowed_names: List[str]):
        self.disallowed_names = disallowed_names
        super().__init__(f"Unsupported attachments: {', '.join(disallowed_names)}")


def _normalize_extension(filename: str) -> str:
    """Normalize a filename's extension to lowercase with leading dot.

    Args:
        filename: The filename to normalize.

    Returns:
        The normalized extension (e.g., '.txt'), or empty string if no extension.
    """
    _, ext = os.path.splitext(filename)
    return ext.lower()


def raise_if_unsupported(email_obj, allowed_exts: List[str]) -> None:
    """Raise UnsupportedAttachmentError if email contains disallowed extensions.

    Args:
        email_obj: The parsed email message object.
        allowed_exts: List of allowed file extensions (e.g., ['.txt', '.md']).

    Raises:
        UnsupportedAttachmentError: If any attachment has a disallowed extension.
    """
    disallowed_names: List[str] = []

    # Normalize allowed extensions for comparison
    allowed_exts_normalized = [ext.lower() for ext in allowed_exts]

    # Walk through all parts of the email
    if email_obj.is_multipart():
        for part in email_obj.walk():
            # Skip non-attachment parts (e.g., multipart container)
            content_disposition = part.get_content_disposition()
            if content_disposition is None:
                continue

            # Check if this is an attachment
            if content_disposition == 'attachment':
                filename = part.get_filename()
                if filename is None:
                    continue

                ext = _normalize_extension(filename)
                if ext not in allowed_exts_normalized:
                    disallowed_names.append(filename)
    else:
        # Single part message - check if it's an attachment
        content_disposition = email_obj.get_content_disposition()
        if content_disposition == 'attachment':
            filename = email_obj.get_filename()
            if filename is not None:
                ext = _normalize_extension(filename)
                if ext not in allowed_exts_normalized:
                    disallowed_names.append(filename)

    # Raise exception if any disallowed attachments found
    if disallowed_names:
        raise UnsupportedAttachmentError(disallowed_names)


def _is_allowed_attachment(part, allowed_exts_normalized: List[str]) -> bool:
    """Check if an email part is an allowed attachment.

    Args:
        part: The email part to check.
        allowed_exts_normalized: List of normalized allowed extensions.

    Returns:
        True if this is an attachment with an allowed extension, False otherwise.
    """
    content_disposition = part.get_content_disposition()
    if content_disposition is None:
        return False

    if content_disposition != 'attachment':
        return False

    filename = part.get_filename()
    if filename is None:
        return False

    ext = _normalize_extension(filename)
    return ext in allowed_exts_normalized


def read_allowed_attachments(email_obj, allowed_exts: List[str]) -> List[Tuple[str, str]]:
    """Return list of (filename, content) tuples for allowed attachments.

    Args:
        email_obj: The parsed email message object.
        allowed_exts: List of allowed file extensions (e.g., ['.txt', '.md']).

    Returns:
        List of tuples containing (filename, content_string) for each allowed attachment.
       _filename is preserved as-is (original case), content is decoded as text.
    """
    allowed_contents: List[Tuple[str, str]] = []
    allowed_exts_normalized = [ext.lower() for ext in allowed_exts]

    # Walk through all parts of the email
    if email_obj.is_multipart():
        for part in email_obj.walk():
            if not _is_allowed_attachment(part, allowed_exts_normalized):
                continue

            filename = part.get_filename()
            if filename is None:
                continue

            # Get the raw bytes from the attachment
            payload_bytes = part.get_payload(decode=True)
            if payload_bytes is None:
                continue

            # Attempt to decode as UTF-8, fallback to ISO-8859-1
            try:
                content = payload_bytes.decode('utf-8')
            except UnicodeDecodeError:
                content = payload_bytes.decode('iso-8859-1')

            allowed_contents.append((filename, content))
    else:
        # Single part message - check if it's an attachment
        if _is_allowed_attachment(email_obj, allowed_exts_normalized):
            filename = email_obj.get_filename()
            if filename is not None:
                payload_bytes = email_obj.get_payload(decode=True)
                if payload_bytes is not None:
                    try:
                        content = payload_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        content = payload_bytes.decode('iso-8859-1')
                    allowed_contents.append((filename, content))

    return allowed_contents
