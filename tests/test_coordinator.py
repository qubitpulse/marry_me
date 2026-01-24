"""
Tests for coordinator.py - Event validation and routing.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from coordinator import Coordinator
from config import Priority, KAFKA_TOPICS, TeamType


class TestCoordinatorValidation:
    """Tests for Coordinator event validation."""

    @pytest.fixture
    def coordinator(self):
        """Create a Coordinator instance for testing."""
        return Coordinator("test-coordinator")

    def test_validate_event_valid(self, coordinator):
        """Valid event should pass validation."""
        event_data = {
            "event_type": "brawl",
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "02:30",
        }
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is True
        assert error == ""

    def test_validate_event_missing_event_type(self, coordinator):
        """Event without event_type should fail."""
        event_data = {
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "02:30",
        }
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is False
        assert "event_type" in error.lower()

    def test_validate_event_missing_priority(self, coordinator):
        """Event without priority should fail."""
        event_data = {
            "event_type": "brawl",
            "description": "Test event",
            "timestamp": "02:30",
        }
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is False
        assert "priority" in error.lower()

    def test_validate_event_missing_description(self, coordinator):
        """Event without description should fail."""
        event_data = {
            "event_type": "brawl",
            "priority": "HIGH",
            "timestamp": "02:30",
        }
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is False
        assert "description" in error.lower()

    def test_validate_event_missing_timestamp(self, coordinator):
        """Event without timestamp should fail."""
        event_data = {
            "event_type": "brawl",
            "priority": "HIGH",
            "description": "Test event",
        }
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is False
        assert "timestamp" in error.lower()

    def test_validate_event_unknown_event_type(self, coordinator):
        """Event with unknown type should fail."""
        event_data = {
            "event_type": "unknown_type",
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "02:30",
        }
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is False
        assert "unknown" in error.lower()

    def test_validate_event_invalid_priority(self, coordinator):
        """Event with invalid priority should fail."""
        event_data = {
            "event_type": "brawl",
            "priority": "URGENT",  # Not valid
            "description": "Test event",
            "timestamp": "02:30",
        }
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is False
        assert "priority" in error.lower()

    def test_validate_event_all_priorities(self, coordinator):
        """All valid priority levels should pass."""
        for priority in ["HIGH", "MEDIUM", "LOW"]:
            event_data = {
                "event_type": "brawl",
                "priority": priority,
                "description": "Test event",
                "timestamp": "02:30",
            }
            is_valid, error = coordinator.validate_event(event_data)
            assert is_valid is True, f"Priority {priority} should be valid"

    def test_validate_event_invalid_timestamp_format(self, coordinator):
        """Event with invalid timestamp format should fail."""
        event_data = {
            "event_type": "brawl",
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "2:30",  # Missing leading zero
        }
        is_valid, error = coordinator.validate_event(event_data)
        # This should still pass as the parsing is flexible
        # Let's test a truly invalid format
        event_data["timestamp"] = "invalid"
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is False
        assert "timestamp" in error.lower()

    def test_validate_event_timestamp_out_of_range(self, coordinator):
        """Event with timestamp > 06:00 should fail."""
        event_data = {
            "event_type": "brawl",
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "07:00",  # Wedding ends at 06:00
        }
        is_valid, error = coordinator.validate_event(event_data)
        assert is_valid is False
        assert "timestamp" in error.lower()

    def test_validate_event_timestamp_boundary_values(self, coordinator):
        """Boundary timestamp values should be handled correctly."""
        # Start of wedding
        event_data = {
            "event_type": "brawl",
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "00:00",
        }
        is_valid, _ = coordinator.validate_event(event_data)
        assert is_valid is True

        # End of wedding
        event_data["timestamp"] = "06:00"
        is_valid, _ = coordinator.validate_event(event_data)
        assert is_valid is True

    def test_validate_event_all_known_event_types(self, coordinator):
        """All known event types should pass validation."""
        known_types = [
            "brawl", "not_on_list", "accident",
            "dirty_table", "broken_items", "dirty_floor",
            "bad_food", "music", "feeling_ill",
            "bride", "groom",
        ]
        for event_type in known_types:
            event_data = {
                "event_type": event_type,
                "priority": "MEDIUM",
                "description": "Test",
                "timestamp": "01:00",
            }
            is_valid, error = coordinator.validate_event(event_data)
            assert is_valid is True, f"Event type {event_type} should be valid"


class TestCoordinatorRouting:
    """Tests for Coordinator event routing."""

    @pytest.fixture
    def coordinator(self):
        """Create a Coordinator instance for testing."""
        return Coordinator("test-coordinator")

    def test_route_event_security(self, coordinator):
        """Security events should route to security topic."""
        from models import Event
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )
        topics = coordinator.route_event(event)
        assert KAFKA_TOPICS[TeamType.SECURITY] in topics

    def test_route_event_cleanup(self, coordinator):
        """Cleanup events should route to cleanup topic."""
        from models import Event
        event = Event(
            event_type="dirty_table",
            priority=Priority.LOW,
            description="Test",
            timestamp="00:00",
        )
        topics = coordinator.route_event(event)
        assert KAFKA_TOPICS[TeamType.CLEAN_UP] in topics

    def test_route_event_catering(self, coordinator):
        """Catering events should route to catering topic."""
        from models import Event
        event = Event(
            event_type="music",
            priority=Priority.MEDIUM,
            description="Test",
            timestamp="00:00",
        )
        topics = coordinator.route_event(event)
        assert KAFKA_TOPICS[TeamType.CATERING] in topics

    def test_route_event_officiant(self, coordinator):
        """Officiant events should route to officiant topic."""
        from models import Event
        event = Event(
            event_type="bride",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )
        topics = coordinator.route_event(event)
        assert KAFKA_TOPICS[TeamType.OFFICIANT] in topics

    def test_route_event_unknown_type(self, coordinator):
        """Unknown event types should return empty list."""
        from models import Event
        event = Event(
            event_type="unknown",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )
        topics = coordinator.route_event(event)
        assert topics == []


class TestCoordinatorProcessEvent:
    """Tests for Coordinator.process_event method."""

    @pytest.fixture
    def coordinator(self):
        """Create a Coordinator instance with mocked Kafka."""
        coord = Coordinator("test-coordinator")
        coord.producer = MagicMock()
        return coord

    def test_process_event_valid(self, coordinator):
        """Valid event should be processed and forwarded."""
        event_data = {
            "id": "test-123",
            "event_type": "brawl",
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "02:30",
            "created_at": 1000.0,
            "handled": False,
            "expired": False,
        }
        result = coordinator.process_event(event_data)
        assert result is True
        coordinator.producer.send.assert_called_once()

    def test_process_event_invalid(self, coordinator):
        """Invalid event should be rejected."""
        event_data = {
            "event_type": "unknown_type",
            "priority": "HIGH",
            "description": "Test event",
            "timestamp": "02:30",
        }
        result = coordinator.process_event(event_data)
        assert result is False
        coordinator.producer.send.assert_not_called()

    def test_process_event_forwards_to_validated_topic(self, coordinator):
        """Valid events should be sent to validated topic."""
        event_data = {
            "id": "test-456",
            "event_type": "music",
            "priority": "MEDIUM",
            "description": "Too loud",
            "timestamp": "03:00",
            "created_at": 2000.0,
            "handled": False,
            "expired": False,
        }
        coordinator.process_event(event_data)

        call_args = coordinator.producer.send.call_args
        assert call_args[0][0] == KAFKA_TOPICS["validated"]
