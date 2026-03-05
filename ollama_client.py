#!/usr/bin/env python3
"""Ollama client module for calling Ollama API with retry logic."""

import json
import logging
import random
import time
import urllib.error
import urllib.request

from typing import Any, Dict


class OllamaError(Exception):
    """Exception raised when Ollama API calls fail after all retries."""


def call_ollama(prompt: str, config: dict) -> str:
    """Call Ollama API with retry and return response text.

    Args:
        prompt: The prompt string to send to Ollama.
        config: Configuration dictionary containing ollama_api_url, ollama_model,
                and ollama_temperature.

    Returns:
        The assistant's response text from Ollama.

    Raises:
        OllamaError: If all retry attempts fail.
    """
    max_retries = 3
    api_url = config.get('ollama_api_url', '')
    model = config.get('ollama_model', '')
    temperature = config.get('ollama_temperature', 0.7)
    timeout = config.get('ollama_timeout', 600)

    logging.info(f"Calling Ollama API at {api_url}")

    for attempt in range(max_retries):
        try:
            # Build the JSON payload
            payload: Dict[str, Any] = {
                'model': model,
                'prompt': prompt,
                'options': {
                        'temperature': temperature,
                        'num_ctx': 65536,
                        'repeat_penalty': 1.1,
                        'top_k': 40,
                        'top_p': 0.9,
                        'min_p': 0.0,
                        'repeat_last_n': 64,
                        'repeat_penalty': 1.1
                    },
                'think': False,
                'stream': False,
                'keep_alive': 0
            }

            # Make the API call using urllib
            json_data = json.dumps(payload).encode('utf-8')
            logging.debug(json_data)
            req = urllib.request.Request(
                api_url,
                data=json_data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                # Parse response
                result = json.loads(response.read().decode('utf-8'))
                #message_content = result.get('message', {}).get('content', '')
                message_content = result.get('response', '')

            logging.info("Ollama API call succeeded")
            logging.debug(f"message_content={message_content}")
            return message_content

        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            if attempt < max_retries - 1:
                # Calculate backoff time: 2^retry * 0.5 + random(0, 0.5)
                backoff_time = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                logging.debug(
                    f"Ollama API attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {backoff_time:.2f}s..."
                )
                time.sleep(backoff_time)
            else:
                logging.info(f"Ollama API call failed after {max_retries} attempts: {e}")
                raise OllamaError(f"Ollama API failed after {max_retries} attempts: {e}") from e

    # This should not be reached, but just in case
    raise OllamaError(f"Ollama API failed after {max_retries} attempts")
