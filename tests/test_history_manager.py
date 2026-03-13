#!/usr/bin/env python3
"""Tests for history_manager module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from history_manager import (
    get_thread_root_id,
    get_history_paths,
    get_recent_history,
    build_prompt_history,
    estimate_prompt_size,
    append_turn,
    needs_post_reply_compact,
    needs_pre_reply_compact,
)


class TestGetThreadRootId:
    def test_uses_first_reference(self):
        headers = {'references': '<root@ex.com> <mid@ex.com>', 'message_id': '<own@ex.com>'}
        assert get_thread_root_id(headers) == 'root@ex.com'

    def test_falls_back_to_in_reply_to(self):
        headers = {'references': '', 'in_reply_to': '<parent@ex.com>', 'message_id': '<own@ex.com>'}
        assert get_thread_root_id(headers) == 'parent@ex.com'

    def test_falls_back_to_message_id(self):
        headers = {'references': '', 'in_reply_to': '', 'message_id': '<own@ex.com>'}
        assert get_thread_root_id(headers) == 'own@ex.com'

    def test_strips_angle_brackets(self):
        headers = {'references': '<abc@ex.com>'}
        assert get_thread_root_id(headers) == 'abc@ex.com'


class TestGetHistoryPaths:
    def test_returns_two_paths(self):
        headers = {'subject': 'Hello World', 'message_id': '<abc@ex.com>'}
        config = {'history_folder': '/tmp/hist'}
        h, c = get_history_paths(headers, config)
        assert h.suffix == '.txt'
        assert str(c).endswith('-compact.txt')

    def test_subject_sanitized(self):
        headers = {'subject': 'Hello World!', 'message_id': '<abc@ex.com>'}
        config = {'history_folder': '/tmp/hist'}
        h, _ = get_history_paths(headers, config)
        assert 'hello_world_' in h.name or 'hello_world' in h.name

    def test_default_history_folder(self):
        headers = {'subject': 'test', 'message_id': '<x@y>'}
        config = {}
        h, _ = get_history_paths(headers, config)
        assert h.parent == Path('history')

    def test_paths_share_base_name(self):
        headers = {'subject': 'topic', 'message_id': '<id@ex.com>'}
        config = {'history_folder': '/tmp/h'}
        h, c = get_history_paths(headers, config)
        # compact file name should be history name with -compact inserted before .txt
        assert c.name == h.name.replace('.txt', '-compact.txt')


class TestGetRecentHistory:
    def test_missing_file_returns_empty(self, tmp_path):
        result = get_recent_history(tmp_path / 'nonexistent.txt')
        assert result == ''

    def test_no_marker_returns_full_content(self, tmp_path):
        f = tmp_path / 'hist.txt'
        f.write_text('User:\nhello\n\nAssistant:\nhi')
        assert get_recent_history(f) == 'User:\nhello\n\nAssistant:\nhi'

    def test_returns_content_after_marker(self, tmp_path):
        f = tmp_path / 'hist.txt'
        f.write_text(
            'User:\nold msg\n\nAssistant:\nold reply'
            '\n\n=== COMPACTED: 2026-01-01 ==='
            '\n\nUser:\nnew msg\n\nAssistant:\nnew reply'
        )
        result = get_recent_history(f)
        assert 'new msg' in result
        assert 'old msg' not in result
        assert 'COMPACTED' not in result

    def test_multiple_markers_uses_last(self, tmp_path):
        f = tmp_path / 'hist.txt'
        f.write_text(
            'User:\nfirst\n\n=== COMPACTED: 2026-01-01 ===\n\n'
            'User:\nsecond\n\n=== COMPACTED: 2026-02-01 ===\n\n'
            'User:\nthird'
        )
        result = get_recent_history(f)
        assert 'third' in result
        assert 'second' not in result
        assert 'first' not in result


class TestBuildPromptHistory:
    def test_both_empty_returns_empty(self, tmp_path):
        result = build_prompt_history(tmp_path / 'h.txt', tmp_path / 'c.txt')
        assert result == ''

    def test_only_recent(self, tmp_path):
        h = tmp_path / 'h.txt'
        h.write_text('User:\nhello\n\nAssistant:\nhi')
        result = build_prompt_history(h, tmp_path / 'c.txt')
        assert result == 'User:\nhello\n\nAssistant:\nhi'

    def test_only_compact(self, tmp_path):
        c = tmp_path / 'c.txt'
        c.write_text('Summary of convo')
        result = build_prompt_history(tmp_path / 'h.txt', c)
        assert '[Conversation summary]' in result
        assert 'Summary of convo' in result

    def test_both_present(self, tmp_path):
        h = tmp_path / 'h.txt'
        h.write_text('User:\nnew\n\nAssistant:\nreply')
        c = tmp_path / 'c.txt'
        c.write_text('Compact summary')
        result = build_prompt_history(h, c)
        assert '[Conversation summary]' in result
        assert '[Recent conversation]' in result
        assert 'Compact summary' in result
        assert 'new' in result


class TestAppendTurn:
    def test_creates_file_on_first_turn(self, tmp_path):
        h = tmp_path / 'hist.txt'
        append_turn(h, 'hello', 'hi there')
        content = h.read_text()
        assert 'User:\nhello' in content
        assert 'Assistant:\nhi there' in content

    def test_appends_subsequent_turns(self, tmp_path):
        h = tmp_path / 'hist.txt'
        append_turn(h, 'first', 'reply1')
        append_turn(h, 'second', 'reply2')
        content = h.read_text()
        assert 'first' in content
        assert 'second' in content
        assert content.index('first') < content.index('second')

    def test_creates_parent_dirs(self, tmp_path):
        h = tmp_path / 'sub' / 'dir' / 'hist.txt'
        append_turn(h, 'msg', 'resp')
        assert h.exists()

    def test_format_correct(self, tmp_path):
        h = tmp_path / 'h.txt'
        append_turn(h, 'my question', 'my answer')
        content = h.read_text()
        assert content == 'User:\nmy question\n\nAssistant:\nmy answer'


class TestNeedsCompact:
    def test_post_reply_false_when_below_threshold(self, tmp_path):
        h = tmp_path / 'h.txt'
        h.write_text('short content')
        config = {'history_compact_threshold_chars': 40000}
        assert not needs_post_reply_compact(h, config)

    def test_post_reply_true_when_above_threshold(self, tmp_path):
        h = tmp_path / 'h.txt'
        h.write_text('x' * 50000)
        config = {'history_compact_threshold_chars': 40000}
        assert needs_post_reply_compact(h, config)

    def test_pre_reply_false_when_below_max(self, tmp_path):
        h = tmp_path / 'h.txt'
        h.write_text('short')
        c = tmp_path / 'c.txt'
        config = {'history_max_prompt_chars': 60000}
        assert not needs_pre_reply_compact(h, c, 'new message', config)

    def test_pre_reply_true_when_above_max(self, tmp_path):
        h = tmp_path / 'h.txt'
        h.write_text('x' * 70000)
        c = tmp_path / 'c.txt'
        config = {'history_max_prompt_chars': 60000}
        assert needs_pre_reply_compact(h, c, 'new message', config)
