#!/usr/bin/env python3
"""Tests for smtp_sender module."""
import logging
import re
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email import utils
from unittest.mock import MagicMock, Mock, patch

import pytest

from smtp_sender import (
    compose_reply_msg,
    generate_message_id,
    send_email,
    send_unsupported_attachment_notice,
    send_api_failure_notice,
)


class TestGenerateMessageId:
    """Tests for generate_message_id function."""

    def test_generate_message_id_format(self):
        """Test that message ID has correct format with 32 hex digits."""
        original_headers = {'message_id': '<test@example.com>'}
        error_msg = ''
        config = {}

        msg_id = generate_message_id(original_headers, error_msg, config)

        # Check format: <32hexdigits@gcfl.net>
        pattern = r'^<[0-9a-f]{32}@gcfl\.net>$'
        assert re.match(pattern, msg_id), f"Message ID {msg_id} doesn't match expected format"

    def test_generate_message_id_random(self):
        """Test that generated IDs are random."""
        original_headers = {}
        error_msg = ''
        config = {}

        id1 = generate_message_id(original_headers, error_msg, config)
        id2 = generate_message_id(original_headers, error_msg, config)

        assert id1 != id2, "Message IDs should be different"

    def test_generate_message_id_uses_32_digits(self):
        """Test that exactly 32 hex digits are generated."""
        original_headers = {}
        error_msg = ''
        config = {}

        msg_id = generate_message_id(original_headers, error_msg, config)

        # Extract the hex part
        match = re.match(r'^<([0-9a-f]+)@gcfl\.net>$', msg_id)
        assert match, f"Message ID {msg_id} doesn't match expected format"
        assert len(match.group(1)) == 32, f"Expected 32 hex digits, got {len(match.group(1))}"


class TestComposeReplyMsg:
    """Tests for compose_reply_msg function."""

    def test_subject_prefix_idempotent(self):
        """Test that subject with 'Re: ' prefix doesn't get another prefix."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Re: hi',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': 'Original body',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        assert msg['Subject'] == 'Re: hi', f"Subject should be 'Re: hi', got '{msg['Subject']}'"

    def test_subject_adds_re_prefix(self):
        """Test that subject without 'Re: ' gets prefix added."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': 'Original body',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        assert msg['Subject'] == 'Re: Hello', f"Subject should be 'Re: Hello', got '{msg['Subject']}'"

    def test_body_format_correct(self):
        """Test that body has correct format with AI reply and original quoted."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': 'Original body content',
            'date': 'Wed, 15 May 2024 10:00:00 +0000',
        }
        reply_text = 'Hello! I can help.'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        # Get the first (and only) payload part - decode base64 content
        payload = msg.get_payload()
        text_part = payload[0] if payload else None
        body_str = text_part.get_payload(decode=True).decode('utf-8') if text_part else ''

        # Check that chat history and AI reply are present
        assert 'Original body content' in body_str
        assert 'Assistant:' in body_str
        assert 'Hello! I can help.' in body_str

    def test_date_fallback(self):
        """Test that missing Date header falls back to current time."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': 'Original body',
            # No date header
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        # Date should be present
        assert msg['Date'] is not None
        # Should be a valid date format
        try:
            parsed_date = utils.parsedate_to_datetime(msg['Date'])
            assert parsed_date is not None
        except (TypeError, ValueError) as e:
            pytest.fail(f"Date header is not valid: {msg['Date']}: {e}")

    def test_original_body_preserved(self):
        """Test that original body is preserved without modification."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': 'Line 1\nLine 2\nLine 3',
            'date': 'Wed, 15 May 2024 10:00:00 +0000',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        # Get the text payload - decode base64 content
        payload = msg.get_payload()
        text_part = payload[0] if payload else None
        body = text_part.get_payload(decode=True).decode('utf-8') if text_part else ''

        # Check that original body is preserved exactly
        assert 'Line 1\nLine 2\nLine 3' in body

    def test_to_header_set_correctly(self):
        """Test that To header is set to original sender."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': 'Original body',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        assert msg['To'] == 'john@example.com'

    def test_from_header_set_correctly(self):
        """Test that From header is set to bot email."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': 'Original body',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        assert msg['From'] == 'bot@example.com'

    def test_message_id_generated(self):
        """Test that Message-Id is in correct format."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': 'Original body',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        assert msg['Message-Id'] is not None
        pattern = r'^<[0-9a-f]{32}@gcfl\.net>$'
        assert re.match(pattern, msg['Message-Id'])

    def test_in_reply_to_header_set(self):
        """Test that In-Reply-To is set to original message ID."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '<original@example.com>',
            'body': 'Original body',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        assert msg['In-Reply-To'] == '<msg1@example.com>'

    def test_references_header_set(self):
        """Test that References header includes original references and message ID."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '<ref1@example.com> <ref2@example.com>',
            'in_reply_to': '<original@example.com>',
            'body': 'Original body',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        references = msg['References']
        assert '<ref1@example.com>' in references
        assert '<ref2@example.com>' in references
        assert '<msg1@example.com>' in references

    def test_empty_body_handling(self):
        """Test handling of empty original body."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
            'body': '',
        }
        reply_text = 'AI reply'
        config = {'bot_email': 'bot@example.com'}

        msg = compose_reply_msg(original_headers, reply_text, config)

        # Get the text payload - decode base64 content
        payload = msg.get_payload()
        text_part = payload[0] if payload else None
        body = text_part.get_payload(decode=True).decode('utf-8') if text_part else ''

        assert 'Assistant:' in body
        assert 'AI reply' in body

class TestSendEmail:
    """Tests for send_email function."""

    @patch('smtplib.SMTP')
    def test_send_tls_success(self, mock_smtp_class):
        """Test successful TLS send."""
        mock_server = Mock()
        # smtplib.SMTP returns itself from __enter__ (context manager pattern)
        mock_server.__enter__ = Mock(return_value=mock_server)
        mock_server.__exit__ = Mock(return_value=None)

        # The SMTP() call returns mock_server
        mock_smtp_class.return_value = mock_server

        msg = MIMEMultipart()
        msg['To'] = 'to@example.com'
        msg['From'] = 'from@example.com'

        config = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
        }

        with patch('smtp_sender.utils.parseaddr') as mock_parseaddr:
            mock_parseaddr.side_effect = lambda x: ('', x)
            send_email(msg, config)

        mock_smtp_class.assert_called_once_with('smtp.example.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.sendmail.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_with_cc_header(self, mock_smtp_class):
        """Test sending with CC header included in recipients."""
        mock_server = Mock()
        mock_server.__enter__ = Mock(return_value=mock_server)
        mock_server.__exit__ = Mock(return_value=None)
        mock_smtp_class.return_value = mock_server

        msg = MIMEMultipart()
        msg['To'] = 'to@example.com'
        msg['From'] = 'from@example.com'
        msg['Cc'] = 'cc@example.com'

        config = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
        }

        with patch('smtp_sender.utils.parseaddr') as mock_parseaddr:
            mock_parseaddr.side_effect = lambda x: ('', x)
            send_email(msg, config)

        # Verify sendmail was called with both To and CC addresses
        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        all_recipients = call_args[0][1]  # Second argument is recipients list
        
        # Should include both To and CC recipients
        assert 'to@example.com' in all_recipients
        assert 'cc@example.com' in all_recipients

    @patch('smtplib.SMTP')
    def test_send_without_cc_header(self, mock_smtp_class):
        """Test sending without CC header - only To address."""
        mock_server = Mock()
        mock_server.__enter__ = Mock(return_value=mock_server)
        mock_server.__exit__ = Mock(return_value=None)
        mock_smtp_class.return_value = mock_server

        msg = MIMEMultipart()
        msg['To'] = 'to@example.com'
        msg['From'] = 'from@example.com'

        config = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
        }

        with patch('smtp_sender.utils.parseaddr') as mock_parseaddr:
            mock_parseaddr.side_effect = lambda x: ('', x)
            send_email(msg, config)

        # Verify sendmail was called with only To address
        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        all_recipients = call_args[0][1]  # Second argument is recipients list
        
        # Should only include To recipient
        assert all_recipients == ['to@example.com']

    @patch('smtplib.SMTP')
    def test_send_ssl_success(self, mock_smtp_class):
        """Test successful SSL send."""
        mock_server = Mock()
        mock_server.__enter__ = Mock(return_value=mock_server)
        mock_server.__exit__ = Mock(return_value=None)
        mock_smtp_class.return_value = mock_server

        msg = MIMEMultipart()
        msg['To'] = 'to@example.com'
        msg['From'] = 'from@example.com'

        config = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 465,
            'smtp_use_tls': False,
            'smtp_use_ssl': True,
        }

        with patch('smtp_sender.utils.parseaddr') as mock_parseaddr:
            mock_parseaddr.side_effect = lambda x: ('', x)
            with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
                mock_ssl_server = Mock()
                mock_ssl_server.__enter__ = Mock(return_value=mock_ssl_server)
                mock_ssl_server.__exit__ = Mock(return_value=None)
                mock_smtp_ssl.return_value = mock_ssl_server
                send_email(msg, config)

        mock_smtp_ssl.assert_called_once_with('smtp.example.com', 465)

    @patch('smtplib.SMTP')
    def test_auth_called(self, mock_smtp_class):
        """Test that login is called with correct credentials."""
        mock_server = Mock()
        mock_server.__enter__ = Mock(return_value=mock_server)
        mock_server.__exit__ = Mock(return_value=None)
        mock_smtp_class.return_value = mock_server

        msg = MIMEMultipart()
        msg['To'] = 'to@example.com'
        msg['From'] = 'from@example.com'

        config = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
        }

        with patch('smtp_sender.utils.parseaddr') as mock_parseaddr:
            mock_parseaddr.side_effect = lambda x: ('', x)
            send_email(msg, config)

        mock_server.login.assert_called_once_with('testuser', 'testpass')

    @patch('smtplib.SMTP')
    def test_failure_exits(self, mock_smtp_class):
        """Test that SMTP failure causes sys.exit(1)."""
        mock_smtp_class.side_effect = smtplib.SMTPServerDisconnected()

        msg = MIMEMultipart()
        msg['To'] = 'to@example.com'
        msg['From'] = 'from@example.com'

        config = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
        }

        with pytest.raises(SystemExit) as excinfo:
            with patch('smtp_sender.utils.parseaddr') as mock_parseaddr:
                mock_parseaddr.side_effect = lambda x: ('', x)
                send_email(msg, config)

        assert excinfo.value.code == 1

    @patch('smtplib.SMTP')
    def test_no_hang_on_error(self, mock_smtp_class):
        """Test that program terminates on SMTP failure."""
        mock_smtp_class.side_effect = smtplib.SMTPServerDisconnected()

        msg = MIMEMultipart()
        msg['To'] = 'to@example.com'
        msg['From'] = 'from@example.com'

        config = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_use_ssl': False,
        }

        # The function should raise SystemExit, not hang
        with pytest.raises(SystemExit) as excinfo:
            with patch('smtp_sender.utils.parseaddr') as mock_parseaddr:
                mock_parseaddr.side_effect = lambda x: ('', x)
                send_email(msg, config)

        assert excinfo.value.code == 1


class TestSendUnsupportedAttachmentNotice:
    """Tests for send_unsupported_attachment_notice function."""

    def test_unsupported_notice_body_correct(self):
        """Test that body lists disallowed and allowed types."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_unsupported_attachment_notice(
                  original_headers,
                  ['file.exe', 'script.bat'],
                  ['.txt', '.md'],
                  {'bot_email': 'bot@example.com'}
                )

                # Get the message that was sent
                call_args = mock_send.call_args
                msg = call_args[0][0]

                # Get the text payload - decode base64 content
                payload = msg.get_payload()
                text_part = payload[0] if payload else None
                body = text_part.get_payload(decode=True).decode('utf-8') if text_part else ''

                assert 'We rejected attachments: file.exe, script.bat' in body
                assert 'Allowed types: .txt, .md' in body

    def test_sends_to_original_sender(self):
        """Test that notice is sent to original sender."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_unsupported_attachment_notice(
                  original_headers,
                  ['file.exe'],
                  ['.txt'],
                  {'bot_email': 'bot@example.com'}
                )

                call_args = mock_send.call_args
                msg = call_args[0][0]

                assert msg['To'] == 'john@example.com'

    def test_calls_send_email(self):
        """Test that send_email is invoked."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_unsupported_attachment_notice(
                  original_headers,
                  ['file.exe'],
                  ['.txt'],
                  {'bot_email': 'bot@example.com'}
                )

                mock_send.assert_called_once()

    def test_message_id_generated(self):
        """Test that Message-Id is generated."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_unsupported_attachment_notice(
                  original_headers,
                  ['file.exe'],
                  ['.txt'],
                  {'bot_email': 'bot@example.com'}
                )

                mock_gen_id.assert_called_once()

    def test_in_reply_to_and_references(self):
        """Test that In-Reply-To and References are set."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '<ref1@example.com>',
            'in_reply_to': '<ref2@example.com>',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_unsupported_attachment_notice(
                  original_headers,
                  ['file.exe'],
                  ['.txt'],
                  {'bot_email': 'bot@example.com'}
                )

                call_args = mock_send.call_args
                msg = call_args[0][0]

                assert msg['In-Reply-To'] == '<msg1@example.com>'
                assert '<ref1@example.com>' in msg['References']
                assert '<msg1@example.com>' in msg['References']


class TestSendApiFailureNotice:
    """Tests for send_api_failure_notice function."""

    def test_api_notice_includes_error(self):
        """Test that error message appears in body."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_api_failure_notice(
                  original_headers,
                  'Connection timeout',
                  {'bot_email': 'bot@example.com'}
                )

                # Get the message that was sent
                call_args = mock_send.call_args
                msg = call_args[0][0]

                # Get the text payload - decode base64 content
                payload = msg.get_payload()
                text_part = payload[0] if payload else None
                body = text_part.get_payload(decode=True).decode('utf-8') if text_part else ''

                assert 'AI service failed. Error details: Connection timeout' in body

    def test_sends_to_original_sender(self):
        """Test that notice is sent to original sender."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_api_failure_notice(
                  original_headers,
                  'API error',
                  {'bot_email': 'bot@example.com'}
                )

                call_args = mock_send.call_args
                msg = call_args[0][0]

                assert msg['To'] == 'john@example.com'

    def test_calls_send_email(self):
        """Test that send_email is invoked."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_api_failure_notice(
                  original_headers,
                  'API error',
                  {'bot_email': 'bot@example.com'}
                )

                mock_send.assert_called_once()

    def test_subject_is_error(self):
        """Test that subject is 'Error processing your email'."""
        original_headers = {
            'from': 'john@example.com',
            'subject': 'Hello',
            'message_id': '<msg1@example.com>',
            'references': '',
            'in_reply_to': '',
        }

        with patch('smtp_sender.send_email') as mock_send:
            with patch('smtp_sender.generate_message_id') as mock_gen_id:
                mock_gen_id.return_value = '<abc123@gcfl.net>'
                send_api_failure_notice(
                  original_headers,
                  'API error',
                  {'bot_email': 'bot@example.com'}
                )

                call_args = mock_send.call_args
                msg = call_args[0][0]

                assert msg['Subject'] == 'Error processing your email'
