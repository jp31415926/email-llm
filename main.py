#!/usr/bin/env python3
"""Main orchestrator for the email bot.

Wires all modules together in a polling loop that:
1. Polls source_folder for .eml files
2. Processes each file (parse, validate, call Ollama, compose reply, send)
3. Archives processed files
4. Handles errors appropriately
"""

import logging
import signal
import sys
import time
from pathlib import Path

from config_loader import get_config, ConfigError
from email_parser import parse_email
from attachment_validator import raise_if_unsupported, read_allowed_attachments, UnsupportedAttachmentError
from ollama_prompt import compose_ollama_prompt
from ollama_client import call_ollama, OllamaError
from smtp_sender import compose_reply_msg, send_email, send_unsupported_attachment_notice, send_api_failure_notice

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_email(email_path: Path, config: dict) -> dict:
    """Process a single email file.

    Args:
        email_path: Path to the .eml file to process.
        config: Configuration dictionary.

    Returns:
        The parsed headers dict for error handling.

    Raises:
        UnsupportedAttachmentError: If unsupported attachments found.
        OllamaError: If Ollama API fails after retries.
        SystemExit: On SMTP failure.
    """
    logger.info(f"Processing email: {email_path.name}")

    # Parse the email
    logger.info("Parsing email...")
    headers = parse_email(email_path)
    email_obj = headers.get('email_obj')

    # Read and validate attachments
    logger.info("Reading attachments...")
    allowed_exts = config.get('allowed_attachment_extensions', [])
    attachments = read_allowed_attachments(email_obj, allowed_exts)

    # Raise if any unsupported attachments
    raise_if_unsupported(email_obj, allowed_exts)

    # Compose prompt
    logger.info("Composing prompt...")
    body: str = headers.get('body', '')  # type: ignore
    prompt = compose_ollama_prompt(config, attachments, body)

    # Call Ollama
    logger.info("Calling Ollama...")
    reply_text = call_ollama(prompt, config)

    # Compose reply message
    logger.info("Composing reply...")
    reply_msg = compose_reply_msg(headers, reply_text, config)

    # Send reply
    logger.info("Sending reply...")
    send_email(reply_msg, config)

    # Archive the original email
    logger.info(f"Archiving {email_path.name}")
    processed_folder = Path(config['processed_folder'])
    processed_folder.mkdir(parents=True, exist_ok=True)
    dest_path = processed_folder / email_path.name
    email_path.rename(dest_path)
    logger.info(f"Archived {email_path.name} → {dest_path}")

    return headers


def main() -> None:
    """Main polling loop that processes emails from source_folder."""
    # Load configuration
    try:
        config = get_config()
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Ensure processed folder exists
    processed_folder = Path(config['processed_folder'])
    processed_folder.mkdir(parents=True, exist_ok=True)

    # Set up graceful shutdown on SIGINT
    def shutdown_handler(signum, frame):
        logger.info("Received shutdown signal, exiting...")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    source_folder = Path(config['source_folder'])
    logger.info(f"Monitoring {source_folder} for emails...")

    # Loop forever, polling for emails
    while True:
        try:
            # Find all .eml files sorted by mtime (FIFO order)
            #jp eml_files = sorted(source_folder.glob("*.eml"), key=lambda p: p.stat().st_mtime)
            eml_files = sorted(source_folder.glob("*"), key=lambda p: p.stat().st_mtime)

            if not eml_files:
                # No files to process, wait before polling again
                polling_interval = config.get('polling_interval_seconds', 10)
                logger.debug(f"No emails found. Waiting {polling_interval}s...")
                time.sleep(polling_interval)
                continue

            # Process each file one at a time
            for email_path in eml_files:
                try:
                    logger.info(f"Found file: {email_path.name}")
                    headers = process_email(email_path, config)
                except UnsupportedAttachmentError as e:
                    logger.warning(f"Unsupported attachment error: {e}")
                    # Re-parse the email to get headers
                    headers = parse_email(email_path)
                    allowed_exts = config.get('allowed_attachment_extensions', [])
                    # Send notice to sender - use headers from the failed email
                    try:
                        send_unsupported_attachment_notice(
                            headers, e.disallowed_names, allowed_exts, config
                        )
                        logger.info(f"Notified sender about unsupported attachments")
                    except Exception as send_err:
                        logger.error(f"Failed to send notice: {send_err}")
                    # Archive even on error
                    processed_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = processed_folder / email_path.name
                    email_path.rename(dest_path)
                    logger.info(f"Archived {email_path.name} → {dest_path}")
                except OllamaError as e:
                    logger.error(f"Ollama API error: {e}")
                    # Re-parse the email to get headers
                    headers = parse_email(email_path)
                    allowed_exts = config.get('allowed_attachment_extensions', [])
                    # After retries fail, send notice
                    try:
                        send_api_failure_notice(headers, str(e), config)
                        logger.info("Sent API failure notice to sender")
                    except Exception as send_err:
                        logger.error(f"Failed to send failure notice: {send_err}")
                    # Archive even on error
                    processed_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = processed_folder / email_path.name
                    email_path.rename(dest_path)
                    logger.info(f"Archived {email_path.name} → {dest_path}")
                except SystemExit:
                    # Re-raise SMTP failure exits
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error processing {email_path.name}: {e}")

            # After processing all files, wait before polling again
            polling_interval = config.get('polling_interval_seconds', 10)
            time.sleep(polling_interval)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, exiting...")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)  # Wait before retrying


if __name__ == '__main__':
    main()
