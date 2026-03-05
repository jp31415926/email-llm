#!/usr/bin/env python3
"""Tests for config_loader module."""

import logging
import os
import pytest
from unittest.mock import patch

from config_loader import ConfigError, get_config


class TestGetConfigSuccess:
    """Tests for successful config loading."""
    
    def test_get_config_success(self, monkeypatch):
        """All env vars set → config validated."""
        # Set required environment variables
        monkeypatch.setenv('SMTP_USER', 'test@example.com')
        monkeypatch.setenv('SMTP_PASS', 'secret123')
        
        config = get_config()
        
        # Verify config was returned
        assert isinstance(config, dict)
        
        # Verify env-injected values
        assert config['smtp_username'] == 'test@example.com'
        assert config['smtp_password'] == 'secret123'
        
        # Verify other config values are present and correct
        assert config['source_folder'] == './emails/new'
        assert config['processed_folder'] == './emails/cur'
        assert config['polling_interval_seconds'] == 30
        assert config['bot_name'] == 'Support Bot'
        assert config['bot_email'] == 'bot@example.com'
        assert config['ollama_api_url'] == 'http://localhost:11434/api/generate'
        assert config['ollama_model'] == 'llama3'
        assert config['ollama_temperature'] == 0.7
        assert config['ollama_prefix_prompt'] == 'You are a helpful email assistant.'
        assert config['allowed_attachment_extensions'] == ['.txt', '.md', '.eml']
        assert config['smtp_host'] == 'smtp.example.com'
        assert config['smtp_port'] == 25
        assert config['smtp_use_tls'] is False
        assert config['smtp_use_ssl'] is False
    
    def test_get_config_is_mutable_copy(self, monkeypatch):
        """Returned config is a mutable copy, not the original."""
        monkeypatch.setenv('SMTP_USER', 'test@example.com')
        monkeypatch.setenv('SMTP_PASS', 'secret123')
        
        config = get_config()
        
        # Modify the returned config
        config['source_folder'] = './modified/path'
        config['smtp_username'] = 'modified@example.com'
        
        # Load again and verify original values persist
        config2 = get_config()
        assert config2['source_folder'] == './emails/new'
        assert config2['smtp_username'] == 'test@example.com'


class TestGetConfigLogsSuccess:
    """Tests for successful config logging."""
    
    def test_get_config_logs_success(self, monkeypatch, caplog):
        """Asserts log call at INFO level."""
        caplog.set_level(logging.INFO)
        
        monkeypatch.setenv('SMTP_USER', 'test@example.com')
        monkeypatch.setenv('SMTP_PASS', 'secret123')
        
        config = get_config()
        
        # Verify log was called at INFO level
        assert len(caplog.records) >= 1
        
        info_logs = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_logs) >= 1
        
        # Check that config loaded message is present
        assert "Configuration loaded successfully" in caplog.text


# Additional helper tests
class TestConfigValidationError:
    """Additional tests for config validation."""
    
    def test_get_config_missing_key(self, monkeypatch):
        """Missing required key → raises ConfigError."""
        monkeypatch.setenv('SMTP_USER', 'test@example.com')
        monkeypatch.setenv('SMTP_PASS', 'secret123')
        
        # Mock config with missing key
        from config_loader import REQUIRED_KEYS
        
        # Temporarily modify REQUIRED_KEYS to test
        original_keys = REQUIRED_KEYS.copy()
        try:
            with patch('config_loader.REQUIRED_KEYS', ['source_folder', 'missing_key']):
                with pytest.raises(ConfigError) as exc_info:
                    get_config()
            
            assert "missing_key" in str(exc_info.value)
        finally:
            # Restore original
            with patch('config_loader.REQUIRED_KEYS', original_keys):
                pass
