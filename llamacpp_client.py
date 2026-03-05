#!/usr/bin/env python3
"""llama.cpp server client module for calling the llama.cpp HTTP API with retry logic."""

import json
import logging
import random
import re
import time
import urllib.error
import urllib.request

from typing import Any, Dict


class LlamaCppError(Exception):
    """Exception raised when llama.cpp API calls fail after all retries."""


def call_llamacpp(prompt: str, config: dict) -> str:
    """Call llama.cpp server API with retry and return response text.

    Args:
        prompt: The prompt string to send.
        config: Configuration dictionary containing llamacpp_api_url,
                llamacpp_temperature, and llamacpp_n_predict.

    Returns:
        The generated text content from the llama.cpp server.

    Raises:
        LlamaCppError: If all retry attempts fail.
    """
    max_retries = 3
    api_url = config.get('llamacpp_api_url', 'http://localhost:8080/completion')
    temperature = config.get('llamacpp_temperature', 0.7)
    n_predict = config.get('llamacpp_n_predict', 1024)
    timeout = config.get('llamacpp_timeout', 600)

    logging.info(f"Calling llama.cpp API at {api_url}")

    for attempt in range(max_retries):
        try:
            payload: Dict[str, Any] = {
                'prompt': prompt,
                'temperature': temperature,
                'n_predict': n_predict,
                'repeat_penalty': 1.1,
                'top_k': 40,
                'top_p': 0.9,
                'min_p': 0.0,
                'stream': False,
                'include_thinking': False,
            }

            json_data = json.dumps(payload).encode('utf-8')
            logging.debug(json_data)
            req = urllib.request.Request(
                api_url,
                data=json_data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                message_content = result.get('content', '')

            # Strip <think>...</think> blocks produced by reasoning models
            message_content = re.sub(r'<think>.*?</think>', '', message_content, flags=re.DOTALL).strip()

            logging.info("llama.cpp API call succeeded")
            logging.debug(f"message_content={message_content}")
            return message_content

        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            if attempt < max_retries - 1:
                backoff_time = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                logging.debug(
                    f"llama.cpp API attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {backoff_time:.2f}s..."
                )
                time.sleep(backoff_time)
            else:
                logging.info(f"llama.cpp API call failed after {max_retries} attempts: {e}")
                raise LlamaCppError(
                    f"llama.cpp API failed after {max_retries} attempts: {e}"
                ) from e

    raise LlamaCppError(f"llama.cpp API failed after {max_retries} attempts")
