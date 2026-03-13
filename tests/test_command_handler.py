#!/usr/bin/env python3
"""Tests for command_handler module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from command_handler import handle_command


class TestHandleCommand:
    @pytest.fixture
    def paths(self, tmp_path):
        return tmp_path / 'hist.txt', tmp_path / 'compact.txt'

    @pytest.fixture
    def config(self):
        return {'llm_backend': 'ollama', 'ollama_prefix_prompt': ''}

    def test_unknown_command_returns_error(self, paths, config):
        history_path, compact_path = paths
        result = handle_command('/foo', {}, history_path, compact_path, config)
        assert 'Unknown command: /foo' in result

    def test_unknown_command_case_insensitive(self, paths, config):
        history_path, compact_path = paths
        result = handle_command('/UNKNOWN', {}, history_path, compact_path, config)
        assert 'Unknown command: /unknown' in result

    def test_compact_calls_compact_history(self, paths, config):
        history_path, compact_path = paths
        with patch('command_handler.compact_history') as mock_compact:
            mock_compact.return_value = 'New summary'
            result = handle_command('/compact', {}, history_path, compact_path, config)
            mock_compact.assert_called_once_with(history_path, compact_path, config)
            assert result == 'New summary'

    def test_compact_case_insensitive(self, paths, config):
        history_path, compact_path = paths
        with patch('command_handler.compact_history') as mock_compact:
            mock_compact.return_value = 'Summary'
            result = handle_command('/COMPACT', {}, history_path, compact_path, config)
            mock_compact.assert_called_once()

    def test_empty_command_returns_error(self, paths, config):
        history_path, compact_path = paths
        result = handle_command('', {}, history_path, compact_path, config)
        assert 'Unknown command' in result
