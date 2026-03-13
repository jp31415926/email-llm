#!/usr/bin/env python3
"""Tests for the Ollama client module."""

import json
import logging
from unittest.mock import Mock, patch, MagicMock

import pytest

from ollama_client import OllamaError, call_ollama


class TestCallOllama:
    """Tests for the call_ollama function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'ollama_api_url': 'http://localhost:11434/api/generate',
            'ollama_model': 'llama3',
            'ollama_temperature': 0.7,
        }
        self.prompt = "Test prompt"

    def _create_mock_context_manager(self, response_data=None, error=None):
        """Create a mock context manager for urlopen using MagicMock."""
        # Use MagicMock with __enter__ and __exit__ specified
        mock_cm = MagicMock()
        if error:
            mock_cm.__enter__.side_effect = error
        else:
            # Create the mock response
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(response_data).encode('utf-8')
            mock_cm.__enter__.return_value = mock_response
        mock_cm.__exit__.return_value = False
        return mock_cm

    @patch('ollama_client.urllib.request.urlopen')
    def test_success(self, mock_urlopen):
        """Test successful API call returns correct text."""
        # Setup mock context manager
        mock_response_content = {
            'model': 'llama3',
            'created_at': '2024-05-15T10:30:00.000Z',
            'response': 'Hello, I can help with that.',
            'done': True
        }
        mock_urlopen.return_value = self._create_mock_context_manager(response_data=mock_response_content)

        # Call function
        result = call_ollama(self.prompt, self.config)

        # Assert
        assert result == 'Hello, I can help with that.'
        mock_urlopen.assert_called_once()

        # Verify the request was made with correct parameters
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.full_url == 'http://localhost:11434/api/generate'
        data = json.loads(request.data.decode('utf-8'))
        assert data['model'] == 'llama3'
        assert data['prompt'] == self.prompt
        assert data['options']['temperature'] == 0.7

    @patch('ollama_client.urllib.request.urlopen')
    @patch('ollama_client.time.sleep')
    def test_retry_success(self, mock_sleep, mock_urlopen):
        """Test that recovery works after 2 failed attempts."""
        from urllib.error import URLError

        # Setup: first 2 calls fail, 3rd succeeds
        mock_urlopen.side_effect = [
            self._create_mock_context_manager(error=URLError("Connection error")),
            self._create_mock_context_manager(error=URLError("Timeout")),
            self._create_mock_context_manager(response_data={'response': 'Success on third try'})
        ]

        # Call function
        result = call_ollama(self.prompt, self.config)

        # Assert
        assert result == 'Success on third try'
        assert mock_urlopen.call_count == 3
        assert mock_sleep.call_count == 2  # Only sleep before retrying

    @patch('ollama_client.urllib.request.urlopen')
    @patch('ollama_client.time.sleep')
    def test_max_retries_exceeded(self, mock_sleep, mock_urlopen):
        """Test that OllamaError is raised after all retries fail."""
        from urllib.error import URLError

        mock_urlopen.side_effect = [
            self._create_mock_context_manager(error=URLError("Connection failed")),
            self._create_mock_context_manager(error=URLError("Connection failed")),
            self._create_mock_context_manager(error=URLError("Connection failed")),
        ]

        # Assert raises OllamaError
        with pytest.raises(OllamaError) as exc_info:
            call_ollama(self.prompt, self.config)

        assert "failed after 3 attempts" in str(exc_info.value)
        assert mock_urlopen.call_count == 3
        assert mock_sleep.call_count == 2  # Sleeps between attempts 1-2 and 2-3

    @patch('ollama_client.urllib.request.urlopen')
    @patch('ollama_client.time.sleep')
    def test_backoff_times_correct(self, mock_sleep, mock_urlopen):
        """Test that backoff times match expected values."""
        from urllib.error import URLError

        mock_urlopen.side_effect = [
            self._create_mock_context_manager(error=URLError("Error")),
            self._create_mock_context_manager(error=URLError("Error")),
            self._create_mock_context_manager(error=URLError("Error")),
        ]

        # Call function - it will fail after 3 attempts
        try:
            call_ollama(self.prompt, self.config)
        except OllamaError:
            pass

        # Assert sleep times:
        # Retry 0: sleep(2^0 * 0.5 + random) = sleep(0.5 + random(0, 0.5))
        # Retry 1: sleep(2^1 * 0.5 + random) = sleep(1.0 + random(0, 0.5))
        assert mock_sleep.call_count == 2

        # Check the base sleep values (without random jitter)
        call_args_list = mock_sleep.call_args_list
        first_backoff = call_args_list[0][0][0]
        second_backoff = call_args_list[1][0][0]

        # 2^0 * 0.5 = 0.5, with jitter 0.5-1.0
        assert 0.5 <= first_backoff < 1.0
        # 2^1 * 0.5 = 1.0, with jitter 0.5-1.0
        assert 1.0 <= second_backoff < 1.5

    @patch('ollama_client.urllib.request.urlopen')
    def test_http_error_handling(self, mock_urlopen):
        """Test that HTTP errors are handled correctly."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = [
            self._create_mock_context_manager(error=HTTPError('http://localhost:11434/api/generate', 404, 'Not Found', [], None)),
            self._create_mock_context_manager(error=HTTPError('http://localhost:11434/api/generate', 404, 'Not Found', [], None)),
            self._create_mock_context_manager(error=HTTPError('http://localhost:11434/api/generate', 404, 'Not Found', [], None)),
        ]

        with pytest.raises(OllamaError):
            call_ollama(self.prompt, self.config)

    @patch('ollama_client.urllib.request.urlopen')
    def test_empty_response_content(self, mock_urlopen):
        """Test handling of response with empty message content."""
        mock_urlopen.return_value = self._create_mock_context_manager(response_data={'message': {'content': ''}})

        result = call_ollama(self.prompt, self.config)
        assert result == ''

    @patch('ollama_client.urllib.request.urlopen')
    def test_missing_message_key(self, mock_urlopen):
        """Test handling of response without message key."""
        mock_urlopen.return_value = self._create_mock_context_manager(response_data={})

        result = call_ollama(self.prompt, self.config)
        assert result == ''

    @patch('ollama_client.urllib.request.urlopen')
    def test_custom_temperature(self, mock_urlopen):
        """Test that custom temperature is used."""
        mock_urlopen.return_value = self._create_mock_context_manager(response_data={'message': {'content': 'OK'}})

        config = {
            'ollama_api_url': 'http://localhost:11434/api/generate',
            'ollama_model': 'llama3',
            'ollama_temperature': 0.9,
        }

        call_ollama("test", config)

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        data = json.loads(request.data.decode('utf-8'))
        assert data['options']['temperature'] == 0.9


    @patch('ollama_client.urllib.request.urlopen')
    def test_os_error_handling(self, mock_urlopen):
        """Test that OSError is caught and retried."""
        mock_urlopen.side_effect = [
            self._create_mock_context_manager(error=OSError("Connection refused")),
            self._create_mock_context_manager(response_data={'response': 'Success'})
        ]

        result = call_ollama(self.prompt, self.config)

        assert result == 'Success'
        assert mock_urlopen.call_count == 2

    def test_log_retries(self, caplog):
        """Test that logs are recorded at correct levels during retries."""
        from urllib.error import URLError

        # Setup caplog to capture root logger logs
        caplog.set_level(logging.DEBUG)

        # Setup: all 3 calls fail
        with patch('ollama_client.urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = [
                self._create_mock_context_manager(error=URLError("API Error")),
                self._create_mock_context_manager(error=URLError("API Error")),
                self._create_mock_context_manager(error=URLError("API Error")),
            ]

            # Call function
            try:
                call_ollama(self.prompt, self.config)
            except OllamaError:
                pass

        # Assert logging calls were made using caplog
        log_messages = [record.message for record in caplog.records]

        # Check for expected log messages (logging goes to root by default)
        assert any("Calling Ollama API" in msg for msg in log_messages), f"Missing 'Calling Ollama API' in {log_messages}"
        assert any("failed after 3 attempts" in msg for msg in log_messages), f"Missing 'failed after 3 attempts' in {log_messages}"
