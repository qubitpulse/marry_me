"""
Tests for team.py - Team management and worker dispatch.
"""
import pytest
import time
import heapq
from unittest.mock import Mock, MagicMock, patch
from multiprocessing import Queue, Value
from ctypes import c_double

from team import TeamManager
from models import Event, Worker
from config import (
    Priority,
    TeamType,
    RoutineType,
    WorkerStatus,
    TEAM_ROUTINES,
    EVENT_HANDLING_TIME_SECONDS,
)


class TestTeamManagerInit:
    """Tests for TeamManager initialization."""

    @pytest.fixture
    def stats_queue(self):
        return Queue()

    @pytest.fixture
    def simulation_start(self):
        return Value(c_double, 0.0)

    def test_team_manager_creation(self, stats_queue, simulation_start):
        """TeamManager should initialize with correct attributes."""
        manager = TeamManager(
            team_type=TeamType.SECURITY,
            num_workers=3,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )
        assert manager.team_type == TeamType.SECURITY
        assert manager.routine == TEAM_ROUTINES[TeamType.SECURITY]
        assert len(manager.team.workers) == 3

    def test_team_manager_workers_have_correct_team(self, stats_queue, simulation_start):
        """All workers should belong to the correct team."""
        manager = TeamManager(
            team_type=TeamType.CATERING,
            num_workers=5,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )
        for worker in manager.team.workers:
            assert worker.team == TeamType.CATERING

    def test_team_manager_workers_start_idle(self, stats_queue, simulation_start):
        """All workers should start in IDLE status."""
        manager = TeamManager(
            team_type=TeamType.WAITERS,
            num_workers=4,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )
        for worker in manager.team.workers:
            assert worker.status == WorkerStatus.IDLE

    def test_team_manager_routine_times(self, stats_queue, simulation_start):
        """TeamManager should have correct routine times."""
        # Security has Standard routine (20, 5)
        manager = TeamManager(
            team_type=TeamType.SECURITY,
            num_workers=1,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )
        assert manager.working_time == 20
        assert manager.idle_time == 5

        # Clean_up has Intermittent routine (5, 5)
        manager = TeamManager(
            team_type=TeamType.CLEAN_UP,
            num_workers=1,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )
        assert manager.working_time == 5
        assert manager.idle_time == 5

        # Catering has Concentrated routine (60, 60)
        manager = TeamManager(
            team_type=TeamType.CATERING,
            num_workers=1,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )
        assert manager.working_time == 60
        assert manager.idle_time == 60


class TestTeamManagerPriorityQueue:
    """Tests for TeamManager priority queue logic."""

    @pytest.fixture
    def manager(self):
        stats_queue = Queue()
        simulation_start = Value(c_double, 0.0)
        return TeamManager(
            team_type=TeamType.SECURITY,
            num_workers=2,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )

    def test_get_priority_value(self, manager):
        """Priority values should be ordered HIGH < MEDIUM < LOW."""
        assert manager.get_priority_value(Priority.HIGH) == 0
        assert manager.get_priority_value(Priority.MEDIUM) == 1
        assert manager.get_priority_value(Priority.LOW) == 2

    def test_add_event_to_queue(self, manager):
        """Events should be added to the queue."""
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )
        manager.add_event_to_queue(event)
        assert len(manager.event_queue) == 1

    def test_get_next_event_empty_queue(self, manager):
        """Getting from empty queue should return None."""
        event = manager.get_next_event()
        assert event is None

    def test_get_next_event_single(self, manager):
        """Should return the only event in queue."""
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )
        manager.add_event_to_queue(event)
        retrieved = manager.get_next_event()
        assert retrieved.id == event.id

    def test_priority_ordering(self, manager):
        """HIGH priority events should come before LOW priority."""
        low_event = Event(
            event_type="brawl",
            priority=Priority.LOW,
            description="Low priority",
            timestamp="00:00",
        )
        high_event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="High priority",
            timestamp="00:00",
        )
        medium_event = Event(
            event_type="brawl",
            priority=Priority.MEDIUM,
            description="Medium priority",
            timestamp="00:00",
        )

        # Add in reverse priority order
        manager.add_event_to_queue(low_event)
        manager.add_event_to_queue(medium_event)
        manager.add_event_to_queue(high_event)

        # Should come out in priority order
        assert manager.get_next_event().priority == Priority.HIGH
        assert manager.get_next_event().priority == Priority.MEDIUM
        assert manager.get_next_event().priority == Priority.LOW

    def test_fifo_within_same_priority(self, manager):
        """Events with same priority should be FIFO ordered."""
        event1 = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="First",
            timestamp="00:00",
            created_at=1000.0,
        )
        event2 = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Second",
            timestamp="00:00",
            created_at=1001.0,
        )

        manager.add_event_to_queue(event2)  # Add second first
        manager.add_event_to_queue(event1)  # Add first second

        # Should get first (earlier created_at) first
        retrieved1 = manager.get_next_event()
        retrieved2 = manager.get_next_event()
        assert retrieved1.description == "First"
        assert retrieved2.description == "Second"


class TestTeamManagerRoutinePhases:
    """Tests for TeamManager routine phase logic."""

    @pytest.fixture
    def manager(self):
        stats_queue = Queue()
        simulation_start = Value(c_double, 1000.0)  # Simulation started at t=1000
        return TeamManager(
            team_type=TeamType.SECURITY,  # Standard routine: 20s work, 5s idle
            num_workers=2,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )

    def test_is_in_idle_phase_before_simulation_start(self):
        """Before simulation starts, should not be in idle phase."""
        stats_queue = Queue()
        simulation_start = Value(c_double, 0.0)  # Not started yet
        manager = TeamManager(
            team_type=TeamType.SECURITY,
            num_workers=1,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )
        assert manager.is_in_idle_phase(1000.0) is False

    def test_is_in_idle_phase_during_working(self, manager):
        """During working phase, should not be in idle phase."""
        # At t=1010, elapsed=10s, cycle position=10 (< 20s working)
        assert manager.is_in_idle_phase(1010.0) is False

    def test_is_in_idle_phase_during_idle(self, manager):
        """During idle phase, should be in idle phase."""
        # At t=1022, elapsed=22s, cycle position=22 (>= 20s working)
        assert manager.is_in_idle_phase(1022.0) is True

    def test_is_in_idle_phase_cycle_repeats(self, manager):
        """Routine should cycle repeatedly."""
        # Standard: 20s work, 5s idle = 25s cycle

        # First cycle
        assert manager.is_in_idle_phase(1010.0) is False  # t=10, working
        assert manager.is_in_idle_phase(1022.0) is True   # t=22, idle

        # Second cycle (t=25-50)
        assert manager.is_in_idle_phase(1030.0) is False  # t=30, position=5, working
        assert manager.is_in_idle_phase(1047.0) is True   # t=47, position=22, idle

    def test_is_in_idle_phase_intermittent(self):
        """Test intermittent routine (5s work, 5s idle)."""
        stats_queue = Queue()
        simulation_start = Value(c_double, 1000.0)
        manager = TeamManager(
            team_type=TeamType.CLEAN_UP,  # Intermittent: 5s work, 5s idle
            num_workers=1,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )

        # t=3, position=3 (< 5s working)
        assert manager.is_in_idle_phase(1003.0) is False

        # t=7, position=7 (>= 5s, in idle)
        assert manager.is_in_idle_phase(1007.0) is True

    def test_is_in_idle_phase_concentrated(self):
        """Test concentrated routine (60s work, 60s idle)."""
        stats_queue = Queue()
        simulation_start = Value(c_double, 1000.0)
        manager = TeamManager(
            team_type=TeamType.CATERING,  # Concentrated: 60s work, 60s idle
            num_workers=1,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )

        # t=30, position=30 (< 60s working)
        assert manager.is_in_idle_phase(1030.0) is False

        # t=90, position=90 (>= 60s, in idle)
        assert manager.is_in_idle_phase(1090.0) is True


class TestTeamManagerExpiredEvents:
    """Tests for TeamManager expired event handling."""

    @pytest.fixture
    def manager(self):
        stats_queue = Queue()
        simulation_start = Value(c_double, 1000.0)
        return TeamManager(
            team_type=TeamType.SECURITY,
            num_workers=2,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )

    def test_check_expired_events_removes_expired(self, manager):
        """Expired events should be removed from queue."""
        # Create an event that's already expired
        expired_event = Event(
            event_type="brawl",
            priority=Priority.HIGH,  # 5 second timeout
            description="Expired",
            timestamp="00:00",
            created_at=990.0,  # Created 10+ seconds ago
        )

        manager.add_event_to_queue(expired_event)
        assert len(manager.event_queue) == 1

        # Check at current time 1005 (event is expired)
        with patch("time.time", return_value=1005.0):
            manager.check_expired_events()

        assert len(manager.event_queue) == 0

    def test_check_expired_events_keeps_valid(self, manager):
        """Valid events should remain in queue."""
        valid_event = Event(
            event_type="brawl",
            priority=Priority.LOW,  # 15 second timeout
            description="Valid",
            timestamp="00:00",
            created_at=1000.0,
        )

        manager.add_event_to_queue(valid_event)

        # Check at current time 1010 (event has 5s remaining)
        with patch("time.time", return_value=1010.0):
            manager.check_expired_events()

        assert len(manager.event_queue) == 1

    def test_check_expired_events_reports_to_stats(self, manager):
        """Expired events should be reported to stats queue."""
        expired_event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Expired",
            timestamp="00:00",
            created_at=990.0,
        )

        manager.add_event_to_queue(expired_event)

        with patch("time.time", return_value=1005.0):
            manager.check_expired_events()

        # Allow queue to sync, then check for item
        time.sleep(0.05)
        try:
            stat = manager.stats_queue.get(timeout=1)
            assert stat["type"] == "expired"
        except Exception:
            pytest.fail("Expected expired event in stats queue")

    def test_check_expired_mixed_events(self, manager):
        """Should correctly separate expired and valid events."""
        expired_event = Event(
            event_type="brawl",
            priority=Priority.HIGH,  # 5s timeout
            description="Expired",
            timestamp="00:00",
            created_at=990.0,
        )
        valid_event = Event(
            event_type="brawl",
            priority=Priority.LOW,  # 15s timeout
            description="Valid",
            timestamp="00:00",
            created_at=1000.0,
        )

        manager.add_event_to_queue(expired_event)
        manager.add_event_to_queue(valid_event)
        assert len(manager.event_queue) == 2

        with patch("time.time", return_value=1005.0):
            manager.check_expired_events()

        # Only valid event should remain
        assert len(manager.event_queue) == 1
        remaining = manager.get_next_event()
        assert remaining.description == "Valid"


class TestTeamManagerHandleEvent:
    """Tests for TeamManager event handling."""

    @pytest.fixture
    def manager(self):
        stats_queue = Queue()
        simulation_start = Value(c_double, 1000.0)
        mgr = TeamManager(
            team_type=TeamType.SECURITY,
            num_workers=2,
            stats_queue=stats_queue,
            simulation_start=simulation_start,
        )
        return mgr

    def test_handle_event_changes_worker_status(self, manager):
        """Handling event should change worker status to WORKING then back to IDLE."""
        worker = manager.team.workers[0]
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )

        assert worker.status == WorkerStatus.IDLE

        # Mock sleep to speed up test
        with patch("time.sleep"):
            manager.handle_event(worker, event)

        assert worker.status == WorkerStatus.IDLE
        assert worker.current_event is None

    def test_handle_event_marks_event_handled(self, manager):
        """Handling event should mark event as handled."""
        worker = manager.team.workers[0]
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )

        with patch("time.sleep"):
            manager.handle_event(worker, event)

        assert event.handled is True
        assert event.handled_by == worker.id

    def test_handle_event_reports_to_stats(self, manager):
        """Handled event should be reported to stats queue."""
        worker = manager.team.workers[0]
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )

        with patch("time.sleep"):
            manager.handle_event(worker, event)

        # Allow queue to sync, then check for item
        time.sleep(0.05)
        try:
            stat = manager.stats_queue.get(timeout=1)
            assert stat["type"] == "handled"
            assert stat["event"]["id"] == event.id
        except Exception:
            pytest.fail("Expected handled event in stats queue")
