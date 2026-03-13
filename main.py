#!/usr/bin/env python3
"""Main orchestrator for the email bot.

Wires all modules together in a polling loop that:
1. Polls source_folder for .eml files
2. Processes each file (parse, validate, call LLM, compose reply, send)
3. Archives processed files
4. Handles errors appropriately
"""

import logging
import re
import signal
import sys
import time
from pathlib import Path

from config_loader import get_config, ConfigError
from email_parser import parse_email
from attachment_validator import raise_if_unsupported, read_allowed_attachments, UnsupportedAttachmentError
from ollama_prompt import compose_ollama_prompt
from ollama_client import call_ollama, OllamaError
from llamacpp_client import call_llamacpp, LlamaCppError
from reply_formatter import extract_latest_user_message
from smtp_sender import compose_reply_msg, compose_compact_notification_msg, send_email, send_unsupported_attachment_notice, send_api_failure_notice
from history_manager import (
    get_history_paths, build_prompt_history, append_turn,
    compact_history, needs_post_reply_compact, needs_pre_reply_compact,
)
from command_handler import handle_command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _archive(email_path: Path, config: dict) -> None:
    """Move email to processed folder."""
    processed_folder = Path(config['processed_folder'])
    processed_folder.mkdir(parents=True, exist_ok=True)
    dest_path = processed_folder / email_path.name
    email_path.rename(dest_path)
    logger.info(f"Archived {email_path.name} → {dest_path}")


def process_email(email_path: Path, config: dict) -> dict:
    """Process a single email file.

    Args:
        email_path: Path to the email file to process.
        config: Configuration dictionary.

    Returns:
        The parsed headers dict.

    Raises:
        UnsupportedAttachmentError: If unsupported attachments found.
        OllamaError / LlamaCppError: If LLM API fails after retries.
        SystemExit: On SMTP failure.
    """
    logger.info(f"Processing email: {email_path.name}")

    # Parse the email
    headers = parse_email(email_path)
    email_obj = headers.get('email_obj')

    # Read and validate attachments
    allowed_exts = config.get('allowed_attachment_extensions', [])
    attachments = read_allowed_attachments(email_obj, allowed_exts)
    raise_if_unsupported(email_obj, allowed_exts)

    # Extract the latest user message (text before any "On ... wrote:" separator)
    body: str = headers.get('body', '')
    user_message = extract_latest_user_message(body)

    # Resolve history file paths for this thread
    history_path, compact_path = get_history_paths(headers, config)

    # Handle slash commands
    if user_message.startswith('/'):
        logger.info(f"Handling command: {user_message[:80]}")
        reply_text = handle_command(user_message, headers, history_path, compact_path, config)
        reply_msg = compose_reply_msg(headers, reply_text, config)
        send_email(reply_msg, config)
        _archive(email_path, config)
        return headers

    # Pre-reply forced compaction if prompt would be too large
    forced_compact_summary = None
    if needs_pre_reply_compact(history_path, compact_path, user_message, config):
        logger.info("Pre-reply forced compaction triggered")
        forced_compact_summary = compact_history(history_path, compact_path, config)

    # Build history and compose LLM prompt
    history = build_prompt_history(history_path, compact_path)
    logger.info("Composing prompt...")
    prompt = compose_ollama_prompt(config, attachments, user_message, history)

    # Call LLM backend
    backend = config.get('llm_backend', 'ollama')
    if backend == 'llamacpp':
        logger.info("Calling llama.cpp API...")
        reply_text = call_llamacpp(prompt, config)
    else:
        logger.info("Calling Ollama...")
        reply_text = call_ollama(prompt, config)

    # Strip any prompt XML tags the LLM may have echoed
    reply_text = re.sub(r'</?(attachment\b[^>]*)>', '', reply_text).strip()

    # Persist this turn to history
    append_turn(history_path, user_message, reply_text)

    # Compose and send reply (prepend compaction notice if forced compact occurred)
    if forced_compact_summary:
        final_reply = f"[Conversation compacted]\n\n{forced_compact_summary}\n\n---\n\n{reply_text}"
    else:
        final_reply = reply_text

    logger.info("Composing and sending reply...")
    reply_msg = compose_reply_msg(headers, final_reply, config)
    send_email(reply_msg, config)

    # Archive the original email
    _archive(email_path, config)

    # Post-reply auto-compaction check
    if needs_post_reply_compact(history_path, config):
        logger.info("Post-reply auto-compact triggered")
        try:
            new_compact = compact_history(history_path, compact_path, config)
            notif_msg = compose_compact_notification_msg(headers, new_compact, config)
            send_email(notif_msg, config)
            logger.info("Sent compaction notification email")
        except Exception as e:
            logger.error(f"Post-reply compaction failed: {e}")

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
            eml_files = sorted(source_folder.glob("*"), key=lambda p: p.stat().st_mtime)

            if not eml_files:
                polling_interval = config.get('polling_interval_seconds', 10)
                logger.debug(f"No emails found. Waiting {polling_interval}s...")
                time.sleep(polling_interval)
                continue

            for email_path in eml_files:
                try:
                    logger.info(f"Found file: {email_path.name}")
                    process_email(email_path, config)
                except UnsupportedAttachmentError as e:
                    logger.warning(f"Unsupported attachment error: {e}")
                    headers = parse_email(email_path)
                    allowed_exts = config.get('allowed_attachment_extensions', [])
                    try:
                        send_unsupported_attachment_notice(
                            headers, e.disallowed_names, allowed_exts, config
                        )
                        logger.info("Notified sender about unsupported attachments")
                    except Exception as send_err:
                        logger.error(f"Failed to send notice: {send_err}")
                    processed_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = processed_folder / email_path.name
                    email_path.rename(dest_path)
                    logger.info(f"Archived {email_path.name} → {dest_path}")
                except (OllamaError, LlamaCppError) as e:
                    logger.error(f"LLM API error: {e}")
                    headers = parse_email(email_path)
                    try:
                        send_api_failure_notice(headers, str(e), config)
                        logger.info("Sent API failure notice to sender")
                    except Exception as send_err:
                        logger.error(f"Failed to send failure notice: {send_err}")
                    processed_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = processed_folder / email_path.name
                    email_path.rename(dest_path)
                    logger.info(f"Archived {email_path.name} → {dest_path}")
                except SystemExit:
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error processing {email_path.name}: {e}")

            polling_interval = config.get('polling_interval_seconds', 10)
            time.sleep(polling_interval)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, exiting...")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
