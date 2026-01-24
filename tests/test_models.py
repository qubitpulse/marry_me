"""
Tests for models.py - Data models for the wedding simulation.
"""
import pytest
import time
from unittest.mock import patch
from models import Event, Worker, Team, SimulationStats
from config import Priority, WorkerStatus, TeamType, RoutineType


class TestEvent:
    """Tests for Event dataclass."""

    def test_event_creation_basic(self):
        """Event should be created with required fields."""
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test event",
            timestamp="01:30",
        )
        assert event.event_type == "brawl"
        assert event.priority == Priority.HIGH
        assert event.description == "Test event"
        assert event.timestamp == "01:30"

    def test_event_default_values(self):
        """Event should have correct default values."""
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )
        assert event.handled is False
        assert event.handled_by is None
        assert event.expired is False
        assert event.id is not None
        assert len(event.id) == 8  # UUID truncated to 8 chars

    def test_event_auto_generated_id(self):
        """Each event should get a unique ID."""
        event1 = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test 1",
            timestamp="00:00",
        )
        event2 = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test 2",
            timestamp="00:00",
        )
        assert event1.id != event2.id

    def test_event_to_dict(self):
        """Event should serialize to dictionary correctly."""
        event = Event(
            id="test-123",
            event_type="music",
            priority=Priority.MEDIUM,
            description="Too loud",
            timestamp="02:45",
            created_at=1000.0,
        )
        data = event.to_dict()

        assert data["id"] == "test-123"
        assert data["event_type"] == "music"
        assert data["priority"] == "MEDIUM"
        assert data["description"] == "Too loud"
        assert data["timestamp"] == "02:45"
        assert data["created_at"] == 1000.0
        assert data["handled"] is False
        assert data["handled_by"] is None
        assert data["expired"] is False

    def test_event_from_dict(self):
        """Event should deserialize from dictionary correctly."""
        data = {
            "id": "evt-456",
            "event_type": "feeling_ill",
            "priority": "LOW",
            "description": "Guest needs water",
            "timestamp": "03:00",
            "created_at": 2000.0,
            "handled": True,
            "handled_by": "worker-1",
            "expired": False,
        }
        event = Event.from_dict(data)

        assert event.id == "evt-456"
        assert event.event_type == "feeling_ill"
        assert event.priority == Priority.LOW
        assert event.description == "Guest needs water"
        assert event.timestamp == "03:00"
        assert event.created_at == 2000.0
        assert event.handled is True
        assert event.handled_by == "worker-1"
        assert event.expired is False

    def test_event_roundtrip_serialization(self):
        """Event should survive to_dict/from_dict roundtrip."""
        original = Event(
            event_type="bride",
            priority=Priority.HIGH,
            description="Bride needs assistance",
            timestamp="04:00",
        )
        data = original.to_dict()
        restored = Event.from_dict(data)

        assert restored.id == original.id
        assert restored.event_type == original.event_type
        assert restored.priority == original.priority
        assert restored.description == original.description
        assert restored.timestamp == original.timestamp

    def test_event_time_remaining(self):
        """time_remaining should calculate correctly based on priority."""
        current_time = 1000.0
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,  # 5 second timeout
            description="Test",
            timestamp="00:00",
            created_at=998.0,  # Created 2 seconds ago
        )
        # Should have 3 seconds remaining (5 - 2 = 3)
        assert event.time_remaining(current_time) == 3.0

    def test_event_time_remaining_zero_floor(self):
        """time_remaining should not go negative."""
        current_time = 1000.0
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,  # 5 second timeout
            description="Test",
            timestamp="00:00",
            created_at=990.0,  # Created 10 seconds ago (past deadline)
        )
        assert event.time_remaining(current_time) == 0

    def test_event_is_expired_false(self):
        """is_expired should return False when time remains."""
        current_time = 1000.0
        event = Event(
            event_type="brawl",
            priority=Priority.LOW,  # 15 second timeout
            description="Test",
            timestamp="00:00",
            created_at=990.0,  # Created 10 seconds ago
        )
        assert event.is_expired(current_time) is False

    def test_event_is_expired_true(self):
        """is_expired should return True when deadline passed."""
        current_time = 1000.0
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,  # 5 second timeout
            description="Test",
            timestamp="00:00",
            created_at=990.0,  # Created 10 seconds ago
        )
        assert event.is_expired(current_time) is True

    def test_event_expiry_by_priority(self):
        """Different priorities should have different expiry times."""
        current_time = 1000.0
        created_at = 993.0  # 7 seconds ago

        high_event = Event(
            event_type="brawl",
            priority=Priority.HIGH,  # 5s - should be expired
            description="Test",
            timestamp="00:00",
            created_at=created_at,
        )
        medium_event = Event(
            event_type="brawl",
            priority=Priority.MEDIUM,  # 10s - should NOT be expired
            description="Test",
            timestamp="00:00",
            created_at=created_at,
        )
        low_event = Event(
            event_type="brawl",
            priority=Priority.LOW,  # 15s - should NOT be expired
            description="Test",
            timestamp="00:00",
            created_at=created_at,
        )

        assert high_event.is_expired(current_time) is True
        assert medium_event.is_expired(current_time) is False
        assert low_event.is_expired(current_time) is False


class TestWorker:
    """Tests for Worker dataclass."""

    def test_worker_creation(self):
        """Worker should be created with required fields."""
        worker = Worker(id="worker-1", team=TeamType.SECURITY)
        assert worker.id == "worker-1"
        assert worker.team == TeamType.SECURITY

    def test_worker_default_status(self):
        """Worker should start as IDLE."""
        worker = Worker(id="worker-1", team=TeamType.CATERING)
        assert worker.status == WorkerStatus.IDLE
        assert worker.current_event is None

    def test_worker_is_available_when_idle(self):
        """Worker should be available when IDLE."""
        worker = Worker(id="worker-1", team=TeamType.WAITERS)
        assert worker.is_available() is True

    def test_worker_not_available_when_working(self):
        """Worker should not be available when WORKING."""
        worker = Worker(
            id="worker-1",
            team=TeamType.WAITERS,
            status=WorkerStatus.WORKING,
        )
        assert worker.is_available() is False

    def test_worker_with_current_event(self):
        """Worker can have a current event assigned."""
        event = Event(
            event_type="music",
            priority=Priority.LOW,
            description="Test",
            timestamp="00:00",
        )
        worker = Worker(
            id="worker-1",
            team=TeamType.CATERING,
            status=WorkerStatus.WORKING,
            current_event=event,
        )
        assert worker.current_event == event
        assert worker.is_available() is False


class TestTeam:
    """Tests for Team dataclass."""

    def test_team_creation(self):
        """Team should be created with type and routine."""
        team = Team(
            team_type=TeamType.SECURITY,
            routine=RoutineType.STANDARD,
        )
        assert team.team_type == TeamType.SECURITY
        assert team.routine == RoutineType.STANDARD

    def test_team_default_workers(self):
        """Team should start with empty workers list."""
        team = Team(
            team_type=TeamType.CATERING,
            routine=RoutineType.CONCENTRATED,
        )
        assert team.workers == []

    def test_team_working_time_property(self):
        """working_time should return first value of routine tuple."""
        team = Team(
            team_type=TeamType.CLEAN_UP,
            routine=RoutineType.INTERMITTENT,  # (5, 5)
        )
        assert team.working_time == 5

    def test_team_idle_time_property(self):
        """idle_time should return second value of routine tuple."""
        team = Team(
            team_type=TeamType.OFFICIANT,
            routine=RoutineType.CONCENTRATED,  # (60, 60)
        )
        assert team.idle_time == 60

    def test_team_with_workers(self):
        """Team can have workers assigned."""
        workers = [
            Worker(id="w1", team=TeamType.SECURITY),
            Worker(id="w2", team=TeamType.SECURITY),
        ]
        team = Team(
            team_type=TeamType.SECURITY,
            routine=RoutineType.STANDARD,
            workers=workers,
        )
        assert len(team.workers) == 2

    def test_get_available_workers_all_idle(self):
        """Should return all workers when all are idle."""
        workers = [
            Worker(id="w1", team=TeamType.WAITERS, status=WorkerStatus.IDLE),
            Worker(id="w2", team=TeamType.WAITERS, status=WorkerStatus.IDLE),
            Worker(id="w3", team=TeamType.WAITERS, status=WorkerStatus.IDLE),
        ]
        team = Team(
            team_type=TeamType.WAITERS,
            routine=RoutineType.STANDARD,
            workers=workers,
        )
        available = team.get_available_workers()
        assert len(available) == 3

    def test_get_available_workers_some_working(self):
        """Should return only idle workers."""
        workers = [
            Worker(id="w1", team=TeamType.WAITERS, status=WorkerStatus.IDLE),
            Worker(id="w2", team=TeamType.WAITERS, status=WorkerStatus.WORKING),
            Worker(id="w3", team=TeamType.WAITERS, status=WorkerStatus.IDLE),
        ]
        team = Team(
            team_type=TeamType.WAITERS,
            routine=RoutineType.STANDARD,
            workers=workers,
        )
        available = team.get_available_workers()
        assert len(available) == 2
        assert all(w.status == WorkerStatus.IDLE for w in available)

    def test_get_available_workers_none_available(self):
        """Should return empty list when all workers are busy."""
        workers = [
            Worker(id="w1", team=TeamType.WAITERS, status=WorkerStatus.WORKING),
            Worker(id="w2", team=TeamType.WAITERS, status=WorkerStatus.WORKING),
        ]
        team = Team(
            team_type=TeamType.WAITERS,
            routine=RoutineType.STANDARD,
            workers=workers,
        )
        available = team.get_available_workers()
        assert len(available) == 0


class TestSimulationStats:
    """Tests for SimulationStats dataclass."""

    def test_stats_default_values(self):
        """Stats should initialize with zeros."""
        stats = SimulationStats()
        assert stats.total_events == 0
        assert stats.handled_events == 0
        assert stats.expired_events == 0
        assert stats.stress_level == 0

    def test_stats_to_dict(self):
        """Stats should serialize to dictionary."""
        stats = SimulationStats(
            total_events=100,
            handled_events=85,
            expired_events=15,
            stress_level=15,
        )
        data = stats.to_dict()

        assert data["total_events"] == 100
        assert data["handled_events"] == 85
        assert data["expired_events"] == 15
        assert data["stress_level"] == 15
        assert data["success_rate"] == "85.0%"

    def test_stats_success_rate_calculation(self):
        """Success rate should be calculated correctly."""
        stats = SimulationStats(total_events=50, handled_events=45)
        data = stats.to_dict()
        assert data["success_rate"] == "90.0%"

    def test_stats_success_rate_zero_events(self):
        """Success rate should be N/A when no events."""
        stats = SimulationStats()
        data = stats.to_dict()
        assert data["success_rate"] == "N/A"

    def test_stats_success_rate_all_handled(self):
        """Success rate should be 100% when all events handled."""
        stats = SimulationStats(total_events=20, handled_events=20)
        data = stats.to_dict()
        assert data["success_rate"] == "100.0%"

    def test_stats_success_rate_none_handled(self):
        """Success rate should be 0% when no events handled."""
        stats = SimulationStats(total_events=20, handled_events=0)
        data = stats.to_dict()
        assert data["success_rate"] == "0.0%"
