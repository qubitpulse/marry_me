"""
Tests for organizer.py - Event distribution to teams.
"""
import pytest
from unittest.mock import Mock, MagicMock
from organizer import Organizer
from models import Event
from config import Priority, TeamType, KAFKA_TOPICS


class TestOrganizerRouting:
    """Tests for Organizer event routing logic."""

    @pytest.fixture
    def organizer(self):
        """Create an Organizer instance for testing."""
        return Organizer()

    def test_get_target_team_security_events(self, organizer):
        """Security event types should route to Security team."""
        for event_type in ["brawl", "not_on_list"]:
            event = Event(
                event_type=event_type,
                priority=Priority.HIGH,
                description="Test",
                timestamp="00:00",
            )
            team = organizer.get_target_team(event)
            assert team == TeamType.SECURITY

    def test_get_target_team_cleanup_events(self, organizer):
        """Cleanup event types should route to Clean_up team."""
        for event_type in ["dirty_table", "dirty_floor"]:
            event = Event(
                event_type=event_type,
                priority=Priority.LOW,
                description="Test",
                timestamp="00:00",
            )
            team = organizer.get_target_team(event)
            assert team == TeamType.CLEAN_UP

    def test_get_target_team_catering_events(self, organizer):
        """Catering event types should route to Catering team."""
        for event_type in ["music", "feeling_ill"]:
            event = Event(
                event_type=event_type,
                priority=Priority.MEDIUM,
                description="Test",
                timestamp="00:00",
            )
            team = organizer.get_target_team(event)
            assert team == TeamType.CATERING

    def test_get_target_team_officiant_events(self, organizer):
        """Officiant event types should route to Officiant team."""
        for event_type in ["bride", "groom"]:
            event = Event(
                event_type=event_type,
                priority=Priority.HIGH,
                description="Test",
                timestamp="00:00",
            )
            team = organizer.get_target_team(event)
            assert team == TeamType.OFFICIANT

    def test_get_target_team_shared_events(self, organizer):
        """Shared event types should route to first available team."""
        # broken_items is handled by both Clean_up and Waiters
        event = Event(
            event_type="broken_items",
            priority=Priority.MEDIUM,
            description="Test",
            timestamp="00:00",
        )
        team = organizer.get_target_team(event)
        assert team in [TeamType.CLEAN_UP, TeamType.WAITERS]

    def test_get_target_team_unknown_event(self, organizer):
        """Unknown event types should return None."""
        event = Event(
            event_type="unknown_event",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )
        team = organizer.get_target_team(event)
        assert team is None


class TestOrganizerDistribution:
    """Tests for Organizer event distribution."""

    @pytest.fixture
    def organizer(self):
        """Create an Organizer instance with mocked Kafka."""
        org = Organizer()
        org.producer = MagicMock()
        return org

    def test_distribute_event_success(self, organizer):
        """Valid event should be distributed to team topic."""
        event = Event(
            event_type="brawl",
            priority=Priority.HIGH,
            description="Fight at bar",
            timestamp="02:00",
        )
        result = organizer.distribute_event(event)

        assert result is True
        organizer.producer.send.assert_called_once()

        # Check it was sent to security topic
        call_args = organizer.producer.send.call_args
        assert call_args[0][0] == KAFKA_TOPICS[TeamType.SECURITY]

    def test_distribute_event_unknown_type(self, organizer):
        """Unknown event type should not be distributed."""
        event = Event(
            event_type="unknown",
            priority=Priority.HIGH,
            description="Test",
            timestamp="00:00",
        )
        result = organizer.distribute_event(event)

        assert result is False
        organizer.producer.send.assert_not_called()

    def test_distribute_event_preserves_event_data(self, organizer):
        """Distributed event should contain all original data."""
        event = Event(
            id="test-789",
            event_type="music",
            priority=Priority.MEDIUM,
            description="Music too loud",
            timestamp="03:30",
        )
        organizer.distribute_event(event)

        call_args = organizer.producer.send.call_args
        sent_data = call_args[1]["value"]

        assert sent_data["id"] == "test-789"
        assert sent_data["event_type"] == "music"
        assert sent_data["priority"] == "MEDIUM"
        assert sent_data["description"] == "Music too loud"

    def test_distribute_to_each_team(self, organizer):
        """Each team should receive events of their type."""
        test_cases = [
            ("brawl", TeamType.SECURITY),
            ("dirty_table", TeamType.CLEAN_UP),
            ("music", TeamType.CATERING),
            ("bride", TeamType.OFFICIANT),
        ]

        for event_type, expected_team in test_cases:
            organizer.producer.reset_mock()
            event = Event(
                event_type=event_type,
                priority=Priority.HIGH,
                description="Test",
                timestamp="00:00",
            )
            organizer.distribute_event(event)

            call_args = organizer.producer.send.call_args
            topic = call_args[0][0]
            assert topic == KAFKA_TOPICS[expected_team], \
                f"Event {event_type} should go to {expected_team.value}"
