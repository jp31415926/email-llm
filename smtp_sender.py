#!/usr/bin/env python3
"""SMTP sender module for composing and sending email replies."""
import logging
import random
import smtplib
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import utils


class UnsupportedAttachmentError(Exception):
    """Exception raised when an unsupported attachment is detected."""
    def __init__(self, disallowed_names: list[str]):
        self.disallowed_names = disallowed_names
        super().__init__(f"Unsupported attachments: {', '.join(disallowed_names)}")


def generate_message_id(original_headers: dict, error_msg: str, config: dict) -> str:
    """Generate a unique message ID with 32 random hex digits.

    Args:
        original_headers: Original email headers (unused, kept for compatibility).
        error_msg: Error message (unused, kept for compatibility).
        config: Configuration dictionary (unused, kept for compatibility).

    Returns:
        A message ID in the format: <[32 hex digits]@gcfl.net>
    """
    hex_digits = ''.join(random.choices('0123456789abcdef', k=32))
    return f"<{hex_digits}@gcfl.net>"


def compose_reply_msg(original_headers: dict, reply_text: str, config: dict) -> MIMEMultipart:
    """Compose reply message with original email quoted.

    Args:
        original_headers: Dictionary with original email headers:
            - from: Sender email address
            - cc: Original CC
            - subject: Original subject
            - message_id: Original message ID
            - references: Original references
            - in_reply_to: In-reply-to header
            - body: Original email body
        reply_text: AI-generated reply text.
        config: Configuration dictionary with bot_email and other settings.

    Returns:
        MIMEMultipart message object ready to send.
    """
    # Extract original values
    original_from = original_headers.get('from', '')
    original_cc = original_headers.get('cc', '')
    original_subject = original_headers.get('subject', '')
    original_message_id = original_headers.get('message_id', '')
    original_references = original_headers.get('references', '')
    #unused original_in_reply_to = original_headers.get('in_reply_to', '')
    original_body = original_headers.get('body', '')

    # Get bot email from config
    bot_email = config.get('bot_email', 'bot@example.com')

    # Handle subject: add "Re: " prefix if not already present
    subject = original_subject
    if subject and not subject.lower().startswith('re: '):
        subject = f"Re: {subject}"

    # Format the date from original email
    date_str = original_headers.get('date', '')
    if date_str:
        # Parse and re-format the date
        date_tuple = utils.parsedate_to_datetime(date_str)
        if date_tuple:
            formatted_date = utils.format_datetime(date_tuple)
        else:
            formatted_date = utils.formatdate()
    else:
        formatted_date = utils.formatdate()

    # Build the message body
    from_header = original_from
    if from_header:
        # Use parseaddr to extract email for display if there's a display name
        name, addr = utils.parseaddr(from_header)
        if name and name != addr:
            from_header = f"{name} <{addr}>"
        else:
            from_header = addr

    body = f"""{original_body}

Assistant:
{reply_text}

[Place any reply down here at the bottom.]
"""

    # Create the multipart message
    msg = MIMEMultipart()
    msg['To'] = original_from
    if original_cc:
        msg['Cc'] = original_cc
    msg['From'] = bot_email
    msg['Subject'] = subject
    msg['Date'] = formatted_date

    # Add Message-ID, In-Reply-To, and References
    new_message_id = generate_message_id(original_headers, '', config)
    msg['Message-Id'] = new_message_id

    if original_message_id:
        msg['In-Reply-To'] = original_message_id

    # Build References header: original references + original message-id
    references_list = []
    if original_references:
        references_list.append(original_references)
    if original_message_id:
        references_list.append(original_message_id)
    msg['References'] = ' '.join(references_list)

    # Add body as plain text part
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    return msg


def send_email(msg: MIMEMultipart, config: dict) -> None:
    """Send email via SMTP.

    Args:
        msg: MIMEMultipart message to send.
        config: Configuration dictionary with SMTP settings.

    Exits:
        Program exits with code 1 on any SMTP failure.
    """
    smtp_host = config.get('smtp_host', '')
    smtp_port = config.get('smtp_port', 25)
    smtp_use_tls = config.get('smtp_use_tls', False)
    smtp_use_ssl = config.get('smtp_use_ssl', False)
    smtp_username = config.get('smtp_username', '')
    smtp_password = config.get('smtp_password', '')

    logging.info(f"Connecting to SMTP server {smtp_host}:{smtp_port}")

    try:
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)

        with server:
            if smtp_use_tls and not smtp_use_ssl:
                logging.debug("Starting TLS...")
                server.starttls()

            # Auth if credentials provided
            if smtp_username and smtp_password:
                logging.debug("Authenticating...")
                server.login(smtp_username, smtp_password)

            # Send the email
            msg_str = msg.as_string()
            to_addrs = msg.get('To', '')
            from_addr = msg.get('From', '')
            
            # Get CC addresses if they exist
            cc_addrs = []
            cc_header = msg.get('Cc', '')
            if cc_header:
                # Parse CC header which may contain multiple addresses
                cc_addrs = [addr.strip() for addr in cc_header.split(',') if addr.strip()]
                # Parse each address to extract email addresses
                cc_addrs = [utils.parseaddr(addr)[1] for addr in cc_addrs if addr]

            # Combine To and CC recipients
            if to_addrs:
                all_recipients = [to_addrs] + cc_addrs
            else:
                all_recipients = cc_addrs
            
            logging.info(f"Sending email to {to_addrs} and CC: {cc_addrs}")
            server.sendmail(from_addr, all_recipients, msg_str)

        logging.info("Email sent successfully")

    except smtplib.SMTPException as e:
        logging.error(f"SMTP error: {e}")
        sys.exit(1)


def send_unsupported_attachment_notice(
    original_headers: dict,
    disallowed_names: list[str],
    allowed_exts: list[str],
    config: dict
) -> None:
    """Send notice about unsupported attachments.

    Args:
        original_headers: Original email headers.
        disallowed_names: List of disallowed attachment filenames.
        allowed_exts: List of allowed extensions.
        config: Configuration dictionary.
    """
    # Compose error message body
    disallowed_str = ', '.join(disallowed_names)
    allowed_str = ', '.join(allowed_exts)
    body = f"We rejected attachments: {disallowed_str}. Allowed types: {allowed_str}"

    # Get bot email
    bot_email = config.get('bot_email', '')

    # Generate message ID
    new_message_id = generate_message_id(original_headers, '', config)

    # Build message
    msg = MIMEMultipart()
    msg['To'] = original_headers.get('from', '')
    if original_headers.get('cc'):
        msg['Cc'] = original_headers.get('cc')
    msg['From'] = bot_email
    msg['Subject'] = 'Error processing your email'
    msg['Date'] = utils.formatdate()
    msg['Message-Id'] = new_message_id

    # Add In-Reply-To and References if available
    if original_headers.get('message_id'):
        msg['In-Reply-To'] = original_headers['message_id']

    references_list = []
    if original_headers.get('references'):
        references_list.append(original_headers['references'])
    if original_headers.get('message_id'):
        references_list.append(original_headers['message_id'])
    if references_list:
        msg['References'] = ' '.join(references_list)

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    send_email(msg, config)


def send_api_failure_notice(
    original_headers: dict,
    error_msg: str,
    config: dict
) -> None:
    """Send notice about API failure.

    Args:
        original_headers: Original email headers.
        error_msg: Error message from API failure.
        config: Configuration dictionary.
    """
    # Compose error message body
    body = f"AI service failed. Error details: {error_msg}"

    # Get bot email
    bot_email = config.get('bot_email', '')

    # Generate message ID
    new_message_id = generate_message_id(original_headers, error_msg, config)

    # Build message
    msg = MIMEMultipart()
    msg['To'] = original_headers.get('from', '')
    if original_headers.get('cc'):
        msg['Cc'] = original_headers.get('cc')
    msg['From'] = bot_email
    msg['Subject'] = 'Error processing your email'
    msg['Date'] = utils.formatdate()
    msg['Message-Id'] = new_message_id

    # Add In-Reply-To and References if available
    if original_headers.get('message_id'):
        msg['In-Reply-To'] = original_headers['message_id']

    references_list = []
    if original_headers.get('references'):
        references_list.append(original_headers['references'])
    if original_headers.get('message_id'):
        references_list.append(original_headers['message_id'])
    if references_list:
        msg['References'] = ' '.join(references_list)

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    send_email(msg, config)
