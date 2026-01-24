"""
Pytest configuration and shared fixtures for Marry Me tests.
"""
import pytest
import tempfile
import shutil
import os
from multiprocessing import Queue, Value
from ctypes import c_double

from models import Event, Worker, Team
from config import Priority, TeamType, RoutineType, WorkerStatus


# ============================================================================
# Event Fixtures
# ============================================================================

@pytest.fixture
def sample_event():
    """Create a basic sample event."""
    return Event(
        event_type="brawl",
        priority=Priority.HIGH,
        description="Test brawl event",
        timestamp="01:30",
    )


@pytest.fixture
def sample_event_data():
    """Create sample event data as dictionary."""
    return {
        "id": "test-001",
        "event_type": "brawl",
        "priority": "HIGH",
        "description": "Test brawl event",
        "timestamp": "01:30",
        "created_at": 1000.0,
        "handled": False,
        "handled_by": None,
        "expired": False,
    }


@pytest.fixture
def event_factory():
    """Factory fixture for creating events with custom parameters."""
    def _create_event(
        event_type="brawl",
        priority=Priority.HIGH,
        description="Test event",
        timestamp="00:00",
        **kwargs
    ):
        return Event(
            event_type=event_type,
            priority=priority,
            description=description,
            timestamp=timestamp,
            **kwargs
        )
    return _create_event


@pytest.fixture
def high_priority_event(event_factory):
    """Create a HIGH priority event."""
    return event_factory(priority=Priority.HIGH)


@pytest.fixture
def medium_priority_event(event_factory):
    """Create a MEDIUM priority event."""
    return event_factory(priority=Priority.MEDIUM)


@pytest.fixture
def low_priority_event(event_factory):
    """Create a LOW priority event."""
    return event_factory(priority=Priority.LOW)


# ============================================================================
# Worker Fixtures
# ============================================================================

@pytest.fixture
def sample_worker():
    """Create a basic sample worker."""
    return Worker(id="worker-test-1", team=TeamType.SECURITY)


@pytest.fixture
def idle_worker():
    """Create an idle worker."""
    return Worker(
        id="worker-idle",
        team=TeamType.WAITERS,
        status=WorkerStatus.IDLE,
    )


@pytest.fixture
def working_worker():
    """Create a working worker."""
    return Worker(
        id="worker-busy",
        team=TeamType.WAITERS,
        status=WorkerStatus.WORKING,
    )


@pytest.fixture
def worker_factory():
    """Factory fixture for creating workers."""
    counter = [0]
    def _create_worker(team=TeamType.SECURITY, status=WorkerStatus.IDLE):
        counter[0] += 1
        return Worker(
            id=f"worker-{counter[0]}",
            team=team,
            status=status,
        )
    return _create_worker


# ============================================================================
# Team Fixtures
# ============================================================================

@pytest.fixture
def sample_team():
    """Create a basic sample team."""
    workers = [
        Worker(id="w1", team=TeamType.SECURITY),
        Worker(id="w2", team=TeamType.SECURITY),
        Worker(id="w3", team=TeamType.SECURITY),
    ]
    return Team(
        team_type=TeamType.SECURITY,
        routine=RoutineType.STANDARD,
        workers=workers,
    )


@pytest.fixture
def team_with_mixed_workers():
    """Create a team with some idle and some working workers."""
    return Team(
        team_type=TeamType.WAITERS,
        routine=RoutineType.STANDARD,
        workers=[
            Worker(id="w1", team=TeamType.WAITERS, status=WorkerStatus.IDLE),
            Worker(id="w2", team=TeamType.WAITERS, status=WorkerStatus.WORKING),
            Worker(id="w3", team=TeamType.WAITERS, status=WorkerStatus.IDLE),
            Worker(id="w4", team=TeamType.WAITERS, status=WorkerStatus.WORKING),
        ],
    )


# ============================================================================
# Multiprocessing Fixtures
# ============================================================================

@pytest.fixture
def stats_queue():
    """Create a multiprocessing Queue for stats."""
    return Queue()


@pytest.fixture
def simulation_start():
    """Create a shared Value for simulation start time."""
    return Value(c_double, 0.0)


@pytest.fixture
def simulation_start_at_1000():
    """Create a shared Value with simulation started at t=1000."""
    return Value(c_double, 1000.0)


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory that's cleaned up after test."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_json_file(temp_dir):
    """Create a temporary JSON file."""
    import json
    filepath = os.path.join(temp_dir, "test_events.json")
    data = [
        {
            "id": "test-1",
            "event_type": "brawl",
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "01:00",
            "created_at": 0,
            "handled": False,
            "expired": False,
        }
    ]
    with open(filepath, 'w') as f:
        json.dump(data, f)
    return filepath


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "kafka: marks tests that require Kafka"
    )
