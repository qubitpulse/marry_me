"""
Tests for simulation.py - Wedding simulation orchestrator.
"""
import pytest
import json
import os
import tempfile
import time
from unittest.mock import Mock, MagicMock, patch

from simulation import WeddingSimulation, EVENT_DESCRIPTIONS
from models import Event, SimulationStats
from config import Priority, TeamType


class TestEventDescriptions:
    """Tests for event description data."""

    def test_all_event_types_have_descriptions(self):
        """All known event types should have descriptions."""
        expected_types = {
            "brawl", "not_on_list", "accident",
            "dirty_table", "broken_items", "dirty_floor",
            "bad_food", "music", "feeling_ill",
            "bride", "groom",
        }
        assert set(EVENT_DESCRIPTIONS.keys()) == expected_types

    def test_descriptions_are_non_empty_lists(self):
        """Each event type should have at least one description."""
        for event_type, descriptions in EVENT_DESCRIPTIONS.items():
            assert isinstance(descriptions, list), f"{event_type} should have list"
            assert len(descriptions) > 0, f"{event_type} should have descriptions"

    def test_descriptions_are_strings(self):
        """All descriptions should be strings."""
        for event_type, descriptions in EVENT_DESCRIPTIONS.items():
            for desc in descriptions:
                assert isinstance(desc, str), f"Description for {event_type} should be string"


class TestWeddingSimulationInit:
    """Tests for WeddingSimulation initialization."""

    def test_simulation_default_values(self):
        """Simulation should initialize with default values."""
        sim = WeddingSimulation()
        assert sim.num_coordinators == 2
        assert sim.workers_per_team == 3
        assert sim.events_file is None

    def test_simulation_custom_values(self):
        """Simulation should accept custom values."""
        sim = WeddingSimulation(
            num_coordinators=5,
            workers_per_team=10,
            events_file="test.json",
        )
        assert sim.num_coordinators == 5
        assert sim.workers_per_team == 10
        assert sim.events_file == "test.json"

    def test_simulation_initial_stats(self):
        """Simulation should start with zero stats."""
        sim = WeddingSimulation()
        assert sim.stats.total_events == 0
        assert sim.stats.handled_events == 0
        assert sim.stats.expired_events == 0
        assert sim.stats.stress_level == 0


class TestWeddingSimulationTimeConversion:
    """Tests for time conversion methods."""

    @pytest.fixture
    def simulation(self):
        return WeddingSimulation()

    def test_simulation_time_to_wedding_time_start(self, simulation):
        """0 seconds should be 00:00."""
        assert simulation.simulation_time_to_wedding_time(0) == "00:00"

    def test_simulation_time_to_wedding_time_one_minute(self, simulation):
        """1 second simulation = 1 minute wedding time."""
        assert simulation.simulation_time_to_wedding_time(1) == "00:01"

    def test_simulation_time_to_wedding_time_one_hour(self, simulation):
        """60 seconds simulation = 1 hour wedding time."""
        assert simulation.simulation_time_to_wedding_time(60) == "01:00"

    def test_simulation_time_to_wedding_time_end(self, simulation):
        """360 seconds = 6 hours (end of wedding)."""
        assert simulation.simulation_time_to_wedding_time(360) == "06:00"

    def test_simulation_time_to_wedding_time_mixed(self, simulation):
        """Test various mixed times."""
        assert simulation.simulation_time_to_wedding_time(90) == "01:30"
        assert simulation.simulation_time_to_wedding_time(150) == "02:30"
        assert simulation.simulation_time_to_wedding_time(337) == "05:37"


class TestWeddingSimulationEventGeneration:
    """Tests for random event generation."""

    @pytest.fixture
    def simulation(self):
        return WeddingSimulation()

    def test_generate_random_event_type(self, simulation):
        """Generated event should have valid event type."""
        event = simulation.generate_random_event("01:00")
        assert event.event_type in EVENT_DESCRIPTIONS.keys()

    def test_generate_random_event_priority(self, simulation):
        """Generated event should have valid priority."""
        event = simulation.generate_random_event("01:00")
        assert event.priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]

    def test_generate_random_event_timestamp(self, simulation):
        """Generated event should have correct timestamp."""
        event = simulation.generate_random_event("03:45")
        assert event.timestamp == "03:45"

    def test_generate_random_event_description(self, simulation):
        """Generated event should have a description."""
        event = simulation.generate_random_event("01:00")
        assert event.description is not None
        assert len(event.description) > 0
        # Description should match one from EVENT_DESCRIPTIONS
        assert event.description in EVENT_DESCRIPTIONS[event.event_type]

    def test_generate_random_event_has_id(self, simulation):
        """Generated event should have unique ID."""
        event1 = simulation.generate_random_event("01:00")
        event2 = simulation.generate_random_event("01:00")
        assert event1.id is not None
        assert event2.id is not None
        assert event1.id != event2.id


class TestWeddingSimulationEventFile:
    """Tests for loading events from file."""

    @pytest.fixture
    def simulation(self):
        return WeddingSimulation()

    def test_load_events_from_file(self, simulation):
        """Should load events from JSON file."""
        events_data = [
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

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(events_data, f)
            temp_path = f.name

        try:
            loaded = simulation.load_events_from_file(temp_path)
            assert len(loaded) == 1
            assert loaded[0]["id"] == "test-1"
            assert loaded[0]["event_type"] == "brawl"
        finally:
            os.unlink(temp_path)

    def test_load_multiple_events_from_file(self, simulation):
        """Should load multiple events from JSON file."""
        events_data = [
            {"id": "1", "event_type": "brawl", "priority": "HIGH",
             "description": "Event 1", "timestamp": "01:00",
             "created_at": 0, "handled": False, "expired": False},
            {"id": "2", "event_type": "music", "priority": "LOW",
             "description": "Event 2", "timestamp": "02:00",
             "created_at": 0, "handled": False, "expired": False},
            {"id": "3", "event_type": "bride", "priority": "MEDIUM",
             "description": "Event 3", "timestamp": "03:00",
             "created_at": 0, "handled": False, "expired": False},
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(events_data, f)
            temp_path = f.name

        try:
            loaded = simulation.load_events_from_file(temp_path)
            assert len(loaded) == 3
        finally:
            os.unlink(temp_path)


class TestNormalizeEventData:
    """Tests for normalizing external dataset formats."""

    def test_normalize_qwasar_format(self):
        """Should normalize QwasarSV dataset format to internal format."""
        raw = {
            "id": 42,
            "event_type": "broken_itens",
            "priority": "High",
            "description": "Broken glass",
            "timestamp": "02:30",
        }
        result = WeddingSimulation._normalize_event_data(raw)
        assert result["id"] == "42"
        assert result["event_type"] == "broken_items"
        assert result["priority"] == "HIGH"
        assert result["created_at"] == 0
        assert result["handled"] is False
        assert result["expired"] is False

    def test_normalize_already_internal_format(self):
        """Should leave already-normalized data unchanged."""
        raw = {
            "id": "evt-001",
            "event_type": "brawl",
            "priority": "HIGH",
            "description": "Fight",
            "timestamp": "01:00",
            "created_at": 100.0,
            "handled": False,
            "expired": False,
        }
        result = WeddingSimulation._normalize_event_data(raw)
        assert result["id"] == "evt-001"
        assert result["priority"] == "HIGH"
        assert result["created_at"] == 100.0

    def test_load_qwasar_format_from_file(self):
        """Should load and normalize QwasarSV-format events from file."""
        sim = WeddingSimulation()
        events_data = [
            {"id": 1, "event_type": "broken_itens", "priority": "Medium",
             "description": "Broken glass", "timestamp": "03:00"},
            {"id": 2, "event_type": "brawl", "priority": "Low",
             "description": "Bar fight", "timestamp": "04:00"},
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(events_data, f)
            temp_path = f.name

        try:
            loaded = sim.load_events_from_file(temp_path)
            assert len(loaded) == 2
            assert loaded[0]["event_type"] == "broken_items"
            assert loaded[0]["priority"] == "MEDIUM"
            assert loaded[0]["id"] == "1"
            assert loaded[1]["priority"] == "LOW"
        finally:
            os.unlink(temp_path)


class TestWeddingSimulationStats:
    """Tests for statistics collection."""

    @pytest.fixture
    def simulation(self):
        return WeddingSimulation()

    def test_collect_stats_handled(self, simulation):
        """Should increment handled_events for handled events."""
        simulation.stats_queue.put({"type": "handled", "event": {}})
        time.sleep(0.05)  # Allow queue to sync
        simulation.collect_stats()
        assert simulation.stats.handled_events == 1

    def test_collect_stats_expired(self, simulation):
        """Should increment expired_events and stress_level for expired events."""
        simulation.stats_queue.put({"type": "expired", "event": {}})
        time.sleep(0.05)  # Allow queue to sync
        simulation.collect_stats()
        assert simulation.stats.expired_events == 1
        assert simulation.stats.stress_level == 1

    def test_collect_stats_multiple(self, simulation):
        """Should correctly count multiple stats."""
        for _ in range(5):
            simulation.stats_queue.put({"type": "handled", "event": {}})
        for _ in range(3):
            simulation.stats_queue.put({"type": "expired", "event": {}})

        time.sleep(0.05)  # Allow queue to sync
        simulation.collect_stats()

        assert simulation.stats.handled_events == 5
        assert simulation.stats.expired_events == 3
        assert simulation.stats.stress_level == 3


class TestWeddingSimulationInjectEvent:
    """Tests for event injection."""

    def test_inject_event_increments_total(self):
        """Injecting event should increment total_events."""
        simulation = WeddingSimulation()
        simulation.producer = MagicMock()

        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test",
            timestamp="01:00",
        )

        simulation.inject_event(event)
        assert simulation.stats.total_events == 1

    def test_inject_event_sends_to_kafka(self):
        """Injecting event should send to Kafka."""
        simulation = WeddingSimulation()
        simulation.producer = MagicMock()

        event = Event(
            event_type="music",
            priority=Priority.MEDIUM,
            description="Test",
            timestamp="02:00",
        )

        simulation.inject_event(event)
        simulation.producer.send.assert_called_once()

    def test_inject_multiple_events(self):
        """Injecting multiple events should increment counter correctly."""
        simulation = WeddingSimulation()
        simulation.producer = MagicMock()

        for i in range(10):
            event = Event(
                event_type="brawl",
                priority=Priority.LOW,
                description=f"Event {i}",
                timestamp="01:00",
            )
            simulation.inject_event(event)

        assert simulation.stats.total_events == 10
        assert simulation.producer.send.call_count == 10


class TestWeddingSimulationResults:
    """Tests for results reporting."""

    def test_print_results_returns_dict(self):
        """print_results should return stats dictionary."""
        simulation = WeddingSimulation()
        simulation.stats = SimulationStats(
            total_events=100,
            handled_events=85,
            expired_events=15,
            stress_level=15,
        )

        results = simulation.print_results()

        assert isinstance(results, dict)
        assert results["total_events"] == 100
        assert results["handled_events"] == 85
        assert results["expired_events"] == 15
        assert results["stress_level"] == 15
        assert results["success_rate"] == "85.0%"
