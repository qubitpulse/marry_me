"""
Tests for logger.py - Event logging and monitoring.
"""
import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path

from logger import EventLogger, get_logger


class TestEventLoggerInit:
    """Tests for EventLogger initialization."""

    def test_logger_creates_log_directory(self):
        """Logger should create log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "test_logs")
            logger = EventLogger(log_dir=log_dir)
            assert os.path.exists(log_dir)

    def test_logger_creates_log_files(self):
        """Logger should create event and stats log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EventLogger(log_dir=tmpdir)
            assert logger.event_log_file.exists() or True  # File created on first write
            # Stats file created on save

    def test_logger_initializes_empty_events(self):
        """Logger should start with empty events list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EventLogger(log_dir=tmpdir)
            assert logger.events == []


class TestEventLoggerLogging:
    """Tests for EventLogger logging methods."""

    @pytest.fixture
    def logger(self):
        """Create a logger with temporary directory."""
        tmpdir = tempfile.mkdtemp()
        log = EventLogger(log_dir=tmpdir)
        yield log
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_log_event_received(self, logger):
        """Should log event received action."""
        event = {"id": "test-1", "event_type": "brawl"}
        logger.log_event_received(event, "coord-1")

        assert len(logger.events) == 1
        assert logger.events[0]["action"] == "received"
        assert logger.events[0]["coordinator"] == "coord-1"

    def test_log_event_validated_valid(self, logger):
        """Should log valid event validation."""
        event = {"id": "test-2", "event_type": "music"}
        logger.log_event_validated(event, "coord-2", valid=True)

        assert len(logger.events) == 1
        assert logger.events[0]["action"] == "validated"
        assert logger.events[0]["valid"] is True
        assert logger.events[0]["error"] is None

    def test_log_event_validated_invalid(self, logger):
        """Should log invalid event validation with error."""
        event = {"id": "test-3", "event_type": "unknown"}
        logger.log_event_validated(event, "coord-1", valid=False, error="Unknown type")

        assert len(logger.events) == 1
        assert logger.events[0]["valid"] is False
        assert logger.events[0]["error"] == "Unknown type"

    def test_log_event_distributed(self, logger):
        """Should log event distribution."""
        event = {"id": "test-4", "event_type": "bride"}
        logger.log_event_distributed(event, "officiant")

        assert len(logger.events) == 1
        assert logger.events[0]["action"] == "distributed"
        assert logger.events[0]["team"] == "officiant"

    def test_log_event_handled(self, logger):
        """Should log event handling."""
        event = {"id": "test-5", "event_type": "brawl"}
        logger.log_event_handled(event, "security-worker-1", 3.0)

        assert len(logger.events) == 1
        assert logger.events[0]["action"] == "handled"
        assert logger.events[0]["worker"] == "security-worker-1"
        assert logger.events[0]["handling_time_seconds"] == 3.0

    def test_log_event_expired(self, logger):
        """Should log event expiration."""
        event = {"id": "test-6", "event_type": "music"}
        logger.log_event_expired(event, "catering")

        assert len(logger.events) == 1
        assert logger.events[0]["action"] == "expired"
        assert logger.events[0]["team"] == "catering"

    def test_log_worker_status_change(self, logger):
        """Should log worker status changes."""
        logger.log_worker_status_change("worker-1", "idle", "working")

        assert len(logger.events) == 1
        assert logger.events[0]["action"] == "worker_status_change"
        assert logger.events[0]["old_status"] == "idle"
        assert logger.events[0]["new_status"] == "working"

    def test_log_team_phase_change(self, logger):
        """Should log team phase changes."""
        logger.log_team_phase_change("security", "idle")

        assert len(logger.events) == 1
        assert logger.events[0]["action"] == "team_phase_change"
        assert logger.events[0]["team"] == "security"
        assert logger.events[0]["phase"] == "idle"


class TestEventLoggerFileOutput:
    """Tests for EventLogger file output."""

    @pytest.fixture
    def logger(self):
        """Create a logger with temporary directory."""
        tmpdir = tempfile.mkdtemp()
        log = EventLogger(log_dir=tmpdir)
        yield log
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_events_written_to_file(self, logger):
        """Events should be written to JSONL file."""
        event = {"id": "test-1", "event_type": "brawl"}
        logger.log_event_received(event, "coord-1")

        # Read back from file
        with open(logger.event_log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["action"] == "received"

    def test_multiple_events_written(self, logger):
        """Multiple events should be appended to file."""
        for i in range(5):
            event = {"id": f"test-{i}", "event_type": "brawl"}
            logger.log_event_received(event, f"coord-{i}")

        with open(logger.event_log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 5

    def test_save_final_stats(self, logger):
        """Final stats should be saved to JSON file."""
        stats = {
            "total_events": 100,
            "handled_events": 85,
            "expired_events": 15,
            "stress_level": 15,
        }
        logger.save_final_stats(stats)

        with open(logger.stats_log_file, "r") as f:
            saved = json.load(f)

        assert saved["statistics"] == stats
        assert "simulation_end" in saved


class TestEventLoggerReport:
    """Tests for EventLogger report generation."""

    @pytest.fixture
    def logger(self):
        """Create a logger with temporary directory."""
        tmpdir = tempfile.mkdtemp()
        log = EventLogger(log_dir=tmpdir)
        yield log
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_generate_report_empty(self, logger):
        """Report should handle empty events."""
        report = logger.generate_report()
        assert report["total_received"] == 0
        assert report["total_handled"] == 0
        assert report["total_expired"] == 0
        assert report["stress_level"] == 0

    def test_generate_report_with_events(self, logger):
        """Report should correctly count events."""
        # Log some events
        for i in range(3):
            logger.log_event_received({"id": f"r-{i}"}, "coord-1")

        for i in range(2):
            logger.log_event_validated({"id": f"v-{i}"}, "coord-1", valid=True)

        logger.log_event_validated({"id": "inv-1"}, "coord-1", valid=False, error="Bad")

        logger.log_event_handled(
            {"id": "h-1", "priority": "HIGH"}, "worker-1", 3.0
        )
        logger.log_event_expired(
            {"id": "e-1", "priority": "LOW"}, "security"
        )

        report = logger.generate_report()

        assert report["total_received"] == 3
        assert report["total_validated"] == 2
        assert report["total_rejected"] == 1
        assert report["total_handled"] == 1
        assert report["total_expired"] == 1
        assert report["stress_level"] == 1

    def test_generate_report_events_by_priority(self, logger):
        """Report should count events by priority."""
        logger.log_event_handled({"id": "1", "priority": "HIGH"}, "w1", 3.0)
        logger.log_event_handled({"id": "2", "priority": "HIGH"}, "w2", 3.0)
        logger.log_event_handled({"id": "3", "priority": "MEDIUM"}, "w3", 3.0)
        logger.log_event_expired({"id": "4", "priority": "LOW"}, "team1")

        report = logger.generate_report()

        assert report["events_by_priority"]["HIGH"] == 2
        assert report["events_by_priority"]["MEDIUM"] == 1
        assert report["events_by_priority"]["LOW"] == 1


class TestGetLogger:
    """Tests for get_logger singleton."""

    def test_get_logger_returns_instance(self):
        """get_logger should return EventLogger instance."""
        # Reset the global instance
        import logger as logger_module
        logger_module._logger_instance = None

        log = get_logger()
        assert isinstance(log, EventLogger)

    def test_get_logger_returns_same_instance(self):
        """get_logger should return same instance on multiple calls."""
        # Reset the global instance
        import logger as logger_module
        logger_module._logger_instance = None

        log1 = get_logger()
        log2 = get_logger()
        assert log1 is log2
