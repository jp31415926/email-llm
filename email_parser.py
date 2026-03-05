#!/usr/bin/env python3
"""Email parser module for extracting headers and body from .eml files."""

from email import policy
from email import utils
from email.parser import BytesParser
from email.message import Message
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Optional
import logging


class TextExtractor(HTMLParser):
    """HTML parser to extract plain text from HTML content."""

    def __init__(self):
        super().__init__()
        self.chunks = []

    def handle_data(self, data: str) -> None:
        self.chunks.append(data)

    def get_text(self) -> str:
        return '\n'.join(self.chunks).strip()


def html_to_plaintext(html: str) -> str:
    """Convert HTML string to plain text."""
    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text()


def parse_email(path: Path) -> Dict[str, Any]:
    """Parse .eml file and return {from, cc, subject, body, message_id, references, in_reply_to, email_obj}."""
    try:
        with open(path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)

        # Extract headers
        from_addr = msg.get('From', '')
        if from_addr:
            from_addr = from_addr.strip()
            # Use email.utils.parseaddr to extract clean email address
            _, parsed_addr = utils.parseaddr(from_addr)
            from_addr = parsed_addr if parsed_addr else from_addr

        subject = msg.get('Subject', '')
        cc = msg.get('Cc', '')
        message_id = msg.get('Message-Id', '')
        references = msg.get('References', '')
        in_reply_to = msg.get('In-Reply-To', '')

        # Extract body - prefer text/plain, fallback to text/html
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    body = part.get_content()
                    break
                elif content_type == 'text/html' and not body:
                    html_content = part.get_content()
                    body = html_to_plaintext(str(html_content))
        else:
            content_type = msg.get_content_type()
            if content_type == 'text/plain':
                body = msg.get_content()
            elif content_type == 'text/html':
                html_content = msg.get_content()
                body = html_to_plaintext(str(html_content))

        return {
            'from': from_addr,
            'cc': cc,
            'subject': subject,
            'body': body,
            'message_id': message_id,
            'references': references,
            'in_reply_to': in_reply_to,
            'date': msg.get('Date', ''),
            'email_obj': msg,
        }

    except Exception as e:
        logging.warning(f"Failed to parse email from {path}: {e}")
        return {
            'from': '',
            'cc': '',
            'subject': '',
            'body': '',
            'message_id': '',
            'references': '',
            'in_reply_to': '',
            'date': '',
            'email_obj': None,
        }
