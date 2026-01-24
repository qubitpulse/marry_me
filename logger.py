"""
Logging and monitoring for the Marry Me wedding simulation.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path


class EventLogger:
    """
    Centralized event logger that writes to both console and file.
    Tracks all events for post-simulation analysis.
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create timestamped log files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.event_log_file = self.log_dir / f"events_{timestamp}.jsonl"
        self.stats_log_file = self.log_dir / f"stats_{timestamp}.json"

        # Setup Python logging
        self.logger = logging.getLogger("marry-me")
        self.logger.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        console_handler.setFormatter(console_format)

        # File handler
        file_handler = logging.FileHandler(self.log_dir / f"simulation_{timestamp}.log")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(file_format)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        # Event storage for analysis
        self.events = []

    def log_event_received(self, event: dict, coordinator_id: str):
        """Log when an event is received by a coordinator."""
        record = {
            "action": "received",
            "timestamp": datetime.now().isoformat(),
            "coordinator": coordinator_id,
            "event": event,
        }
        self._write_event_record(record)
        self.logger.info(
            f"Event {event.get('id')} received by {coordinator_id}"
        )

    def log_event_validated(self, event: dict, coordinator_id: str, valid: bool, error: str = None):
        """Log event validation result."""
        record = {
            "action": "validated",
            "timestamp": datetime.now().isoformat(),
            "coordinator": coordinator_id,
            "event": event,
            "valid": valid,
            "error": error,
        }
        self._write_event_record(record)
        if valid:
            self.logger.info(f"Event {event.get('id')} validated by {coordinator_id}")
        else:
            self.logger.warning(
                f"Event {event.get('id')} rejected by {coordinator_id}: {error}"
            )

    def log_event_distributed(self, event: dict, team: str):
        """Log when an event is distributed to a team."""
        record = {
            "action": "distributed",
            "timestamp": datetime.now().isoformat(),
            "team": team,
            "event": event,
        }
        self._write_event_record(record)
        self.logger.info(
            f"Event {event.get('id')} distributed to {team}"
        )

    def log_event_handled(self, event: dict, worker_id: str, handling_time: float):
        """Log when an event is successfully handled."""
        record = {
            "action": "handled",
            "timestamp": datetime.now().isoformat(),
            "worker": worker_id,
            "handling_time_seconds": handling_time,
            "event": event,
        }
        self._write_event_record(record)
        self.logger.info(
            f"Event {event.get('id')} handled by {worker_id} "
            f"in {handling_time:.2f}s"
        )

    def log_event_expired(self, event: dict, team: str):
        """Log when an event expires without being handled."""
        record = {
            "action": "expired",
            "timestamp": datetime.now().isoformat(),
            "team": team,
            "event": event,
        }
        self._write_event_record(record)
        self.logger.warning(
            f"Event {event.get('id')} EXPIRED in {team} - STRESS INCREASED"
        )

    def log_worker_status_change(self, worker_id: str, old_status: str, new_status: str):
        """Log worker status changes."""
        record = {
            "action": "worker_status_change",
            "timestamp": datetime.now().isoformat(),
            "worker": worker_id,
            "old_status": old_status,
            "new_status": new_status,
        }
        self._write_event_record(record)
        self.logger.debug(f"Worker {worker_id}: {old_status} -> {new_status}")

    def log_team_phase_change(self, team: str, phase: str):
        """Log team routine phase changes (working/idle)."""
        record = {
            "action": "team_phase_change",
            "timestamp": datetime.now().isoformat(),
            "team": team,
            "phase": phase,
        }
        self._write_event_record(record)
        self.logger.debug(f"Team {team} entering {phase} phase")

    def _write_event_record(self, record: dict):
        """Write a record to the event log file (JSONL format)."""
        self.events.append(record)
        with open(self.event_log_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    def save_final_stats(self, stats: dict):
        """Save final simulation statistics."""
        final_report = {
            "simulation_end": datetime.now().isoformat(),
            "statistics": stats,
            "total_logged_events": len(self.events),
        }
        with open(self.stats_log_file, "w") as f:
            json.dump(final_report, f, indent=2)
        self.logger.info(f"Final stats saved to {self.stats_log_file}")

    def generate_report(self) -> dict:
        """Generate a summary report from logged events."""
        handled = [e for e in self.events if e["action"] == "handled"]
        expired = [e for e in self.events if e["action"] == "expired"]
        validated = [e for e in self.events if e["action"] == "validated"]

        # Events by team
        events_by_team = {}
        for e in self.events:
            team = e.get("team")
            if team:
                events_by_team[team] = events_by_team.get(team, 0) + 1

        # Events by priority
        events_by_priority = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for e in handled + expired:
            priority = e.get("event", {}).get("priority")
            if priority in events_by_priority:
                events_by_priority[priority] += 1

        return {
            "total_received": len([e for e in self.events if e["action"] == "received"]),
            "total_validated": len([e for e in validated if e.get("valid")]),
            "total_rejected": len([e for e in validated if not e.get("valid")]),
            "total_handled": len(handled),
            "total_expired": len(expired),
            "events_by_team": events_by_team,
            "events_by_priority": events_by_priority,
            "stress_level": len(expired),
        }


# Global logger instance
_logger_instance = None


def get_logger() -> EventLogger:
    """Get the global EventLogger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = EventLogger()
    return _logger_instance
