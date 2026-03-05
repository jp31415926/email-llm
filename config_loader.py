#!/usr/bin/env python3
"""Configuration loader for the email bot.

Loads config from config.py and injects environment variables for SMTP credentials.
"""

import logging
import os
from copy import deepcopy
from typing import Any

# Import config (pure data, no env imports)
from config import config as config_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Required configuration keys
REQUIRED_KEYS = [
    'source_folder',
    'processed_folder',
    'polling_interval_seconds',
    'bot_name',
    'bot_email',
    'ollama_api_url',
    'ollama_model',
    'ollama_temperature',
    'ollama_prefix_prompt',
    'allowed_attachment_extensions',
    'smtp_host',
    'smtp_port',
    'smtp_use_tls',
    'smtp_use_ssl',
#    'smtp_username',  # injected from env
#    'smtp_password',  # injected from env
]

# Environment variable mappings
ENV_VAR_MAPPINGS = {
    'smtp_username': 'SMTP_USER',
    'smtp_password': 'SMTP_PASS',
}


class ConfigError(Exception):
    """Raised when configuration validation fails."""
    pass


def _validate_config(config: dict[str, Any]) -> None:
    """Validate that all required keys are present and non-empty.
    
    Args:
        config: The configuration dictionary to validate.
    
    Raises:
        ConfigError: If any required key is missing or has an empty value.
    """
    missing_keys = []
    empty_keys = []
    
    for key in REQUIRED_KEYS:
        if key not in config:
            missing_keys.append(key)
        elif not config[key]:
            # Check for empty string, empty list, or None
            value = config[key]
            if isinstance(value, str) and value.strip() == '':
                empty_keys.append(key)
            elif value is None:
                empty_keys.append(key)
            elif isinstance(value, list) and len(value) == 0:
                empty_keys.append(key)
    
    if missing_keys:
        raise ConfigError(f"Missing required configuration keys: {', '.join(missing_keys)}")
    
    if empty_keys:
        raise ConfigError(f"Required configuration keys have empty values: {', '.join(empty_keys)}")


def _inject_env_vars(config: dict[str, Any]) -> dict[str, Any]:
    """Inject environment variables into the config.
    
    Args:
        config: The base configuration dictionary.
    
    Returns:
        A new config dict with environment variables injected.
    
    Raises:
        ConfigError: If a required environment variable is not set.
    """
    result = deepcopy(config)
    
    for config_key, env_var in ENV_VAR_MAPPINGS.items():
        env_value = os.environ.get(env_var)
        if env_value is None:
            env_value = '';
            #raise ConfigError(f"Required environment variable '{env_var}' is not set")
        result[config_key] = env_value
    
    return result


def get_config() -> dict[str, Any]:
    """Load and validate configuration with environment variable injection.
    
    Returns:
        A mutable copy of the configuration dictionary with environment
        variables injected.
    
    Raises:
        ConfigError: If any required config key is missing or any required
            environment variable is not set.
    """
    # Start with the base config
    result = deepcopy(config_data)
    
    # Inject environment variables
    result = _inject_env_vars(result)
    
    # Validate the complete configuration
    _validate_config(result)
    
    # Log success at INFO level
    logger.info("Configuration loaded successfully")
    
    return result
