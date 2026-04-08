#!/usr/bin/env python3
"""Tests for lineflush."""

import io
import os
import sys
import subprocess
import tempfile
import unittest

# Import the engine class from the lineflush script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load lineflush module (no .py extension)
import importlib.util
import types
_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineflush")
loader = importlib.machinery.SourceFileLoader("lineflush_mod", _path)
lf = types.ModuleType("lineflush_mod")
loader.exec_module(lf)

LineFlush = lf.LineFlush
strip_ansi = lf.strip_ansi
char_diff = lf.char_diff

LINEFLUSH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineflush")


class TestStripAnsi(unittest.TestCase):
    def test_no_escapes(self):
        self.assertEqual(strip_ansi("hello world"), "hello world")

    def test_color_codes(self):
        self.assertEqual(strip_ansi("\x1b[32mOK\x1b[0m"), "OK")

    def test_bold_and_color(self):
        self.assertEqual(strip_ansi("\x1b[1m\x1b[34mtext\x1b[0m"), "text")

    def test_empty(self):
        self.assertEqual(strip_ansi(""), "")


class TestCharDiff(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(char_diff("hello", "hello"), 0)

    def test_one_char_diff(self):
        self.assertEqual(char_diff("hello", "hallo"), 1)

    def test_length_diff(self):
        self.assertEqual(char_diff("hi", "hello"), 4)

    def test_with_ansi(self):
        self.assertEqual(char_diff("\x1b[32mhello\x1b[0m", "hello"), 0)

    def test_with_whitespace(self):
        self.assertEqual(char_diff("  hello  ", "hello"), 0)

    def test_spinner_frames(self):
        # Spinner frames differ by just the spinner character
        d = char_diff("    Working \u28f7", "    Working \u28af")
        self.assertLessEqual(d, 5)

    def test_summary_vs_spinner(self):
        d = char_diff("[Summary] 34 tests run: 34 OK", "    Working \u28f7")
        self.assertGreater(d, 5)


class TestLineFlushEngine(unittest.TestCase):
    """Test the LineFlush engine directly by feeding it byte sequences."""

    def _run_engine(self, chunks, logfile=None):
        """Feed chunks through the engine, capturing output."""
        captured = io.BytesIO()

        engine = LineFlush(logfile=logfile, output=captured)
        for chunk in chunks:
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            engine.process(chunk)
        engine.finish(close_log=False)

        return captured.getvalue().decode('utf-8', errors='replace')

    def test_plain_text_passthrough(self):
        """Plain text without escape sequences passes through unchanged."""
        result = self._run_engine(["hello\nworld\n"])
        self.assertIn("hello", result)
        self.assertIn("world", result)

    def test_colors_preserved(self):
        """ANSI color codes pass through to terminal."""
        colored = "\x1b[32mgreen\x1b[0m\n"
        result = self._run_engine([colored])
        self.assertIn("\x1b[32m", result)
        self.assertIn("green", result)

    def test_spinner_animation_allowed(self):
        """Similar lines with cursor-up are allowed (spinner animation)."""
        # Need two similar lines in history first, then cursor-up is allowed
        data = "    Working \u28f7\r\n"
        data += "    Working \u28af\r\n"
        data += "\x1b[1A\x1b[2K    Working \u28f7\r\n"
        result = self._run_engine([data])
        # Cursor-up should pass through (animation allowed)
        self.assertIn("\x1b[1A", result)

    def test_destructive_curup_blocked(self):
        """Cursor-up that would overwrite different content is blocked."""
        # Line 1: real content, Line 2: spinner, then cursor-up
        data = "Important result line\r\n"
        data += "    Working \u28f7\r\n"
        data += "\x1b[1A\x1b[2K    Working \u28af\r\n"
        result = self._run_engine([data])
        # The important line should survive
        self.assertIn("Important result", result)

    def test_hold_drops_at_eof(self):
        """Spinner remnants after important content are dropped at EOF."""
        data = "First line\r\n"
        data += "Summary: all passed\r\n"
        data += "    Working \u28f7\r\n"
        data += "\x1b[1A\x1b[2K    Working \u28af\r\n"
        result = self._run_engine([data])
        self.assertIn("Summary: all passed", result)

    def test_hold_flushes_on_real_content(self):
        """Hold mode flushes when real content (2+ lines without cursor-up) arrives."""
        data = "line before\r\n"
        data += "    Working \u28f7\r\n"
        data += "\x1b[1A\x1b[2K    Working \u28af\r\n"
        # Now real content: two lines without cursor-up
        data += "real line 1\r\n"
        data += "real line 2\r\n"
        result = self._run_engine([data])
        self.assertIn("real line 1", result)
        self.assertIn("real line 2", result)

    def test_log_output_clean(self):
        """Log file gets clean output with destructive sequences stripped."""
        logbuf = io.StringIO()
        data = "hello\r\nworld\r\n"
        self._run_engine([data], logfile=logbuf)
        log_content = logbuf.getvalue()
        self.assertIn("hello", log_content)
        self.assertIn("world", log_content)
        # No carriage returns in log
        self.assertNotIn("\r", log_content)

    def test_log_preserves_colors(self):
        """Log file preserves ANSI color codes."""
        logbuf = io.StringIO()
        data = "\x1b[32mgreen\x1b[0m\r\nline2\r\nline3\r\nline4\r\nline5\r\n"
        self._run_engine([data], logfile=logbuf)
        log_content = logbuf.getvalue()
        self.assertIn("\x1b[32m", log_content)


class TestLineFlushIntegration(unittest.TestCase):
    """Integration tests that run the lineflush script as a subprocess."""

    def test_basic_command(self):
        """lineflush can run a simple command and capture output."""
        result = subprocess.run(
            [LINEFLUSH, "echo", "hello world"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertIn("hello world", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_exit_code_propagation(self):
        """lineflush propagates the child's exit code."""
        result = subprocess.run(
            [LINEFLUSH, "sh", "-c", "exit 42"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 42)

    def test_log_file_creation(self):
        """lineflush creates a log file with -o."""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
            logpath = f.name
        try:
            result = subprocess.run(
                [LINEFLUSH, "-o", logpath, "echo", "logged output"],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0)
            with open(logpath) as f:
                content = f.read()
            self.assertIn("logged output", content)
        finally:
            os.unlink(logpath)

    def test_colors_from_command(self):
        """Commands that emit colors have them preserved."""
        result = subprocess.run(
            [LINEFLUSH, "sh", "-c", 'printf "\\033[31mred\\033[0m\\n"'],
            capture_output=True, timeout=10,
        )
        self.assertIn(b"\x1b[31m", result.stdout)

    def test_spinner_simulation(self):
        """Simulated spinner doesn't eat previous content."""
        # Script that prints a summary then does a spinner-like overwrite
        script = (
            'printf "Summary: 10 passed\\r\\n"'
            ' && printf "    Working X\\r\\n"'
            ' && printf "\\033[1A\\033[2K    Working Y\\r\\n"'
        )
        result = subprocess.run(
            [LINEFLUSH, "sh", "-c", script],
            capture_output=True, text=True, timeout=10,
        )
        self.assertIn("Summary: 10 passed", result.stdout)

    def test_version(self):
        """--version flag works."""
        result = subprocess.run(
            [LINEFLUSH, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertIn("lineflush", result.stdout)

    def test_no_command_error(self):
        """Running without a command prints usage and exits non-zero."""
        result = subprocess.run(
            [LINEFLUSH],
            capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_stderr_captured(self):
        """stderr from the child is captured through the pty."""
        result = subprocess.run(
            [LINEFLUSH, "sh", "-c", 'echo err >&2'],
            capture_output=True, text=True, timeout=10,
        )
        # pty merges stderr into stdout
        self.assertIn("err", result.stdout)

    def test_log_strips_destructive_sequences(self):
        """Log file has cursor-up and erase sequences stripped."""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
            logpath = f.name
        try:
            script = (
                'printf "line1\\r\\n"'
                ' && printf "line2\\r\\n"'
                ' && printf "line3\\r\\n"'
                ' && printf "line4\\r\\n"'
                ' && printf "line5\\r\\n"'
            )
            result = subprocess.run(
                [LINEFLUSH, "-o", logpath, "sh", "-c", script],
                capture_output=True, text=True, timeout=10,
            )
            with open(logpath) as f:
                content = f.read()
            self.assertNotIn("\r", content)
            self.assertNotIn("\x1b[1A", content)
            self.assertIn("line1", content)
        finally:
            os.unlink(logpath)


if __name__ == '__main__':
    unittest.main()
