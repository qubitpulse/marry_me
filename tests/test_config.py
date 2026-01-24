"""
Tests for config.py - Configuration constants and enums.
"""
import pytest
from config import (
    Priority,
    WorkerStatus,
    GuestStatus,
    TeamType,
    RoutineType,
    TEAM_ROUTINES,
    TEAM_EVENT_TYPES,
    EVENT_TYPE_TO_TEAMS,
    KAFKA_TOPICS,
)


class TestPriorityEnum:
    """Tests for Priority enum."""

    def test_priority_values(self):
        """Priority values should match simulation timeframes."""
        assert Priority.HIGH.value == 5
        assert Priority.MEDIUM.value == 10
        assert Priority.LOW.value == 15

    def test_priority_ordering(self):
        """HIGH priority should have lowest timeout value."""
        assert Priority.HIGH.value < Priority.MEDIUM.value < Priority.LOW.value


class TestWorkerStatusEnum:
    """Tests for WorkerStatus enum."""

    def test_worker_status_values(self):
        """Worker status should have idle and working states."""
        assert WorkerStatus.IDLE.value == "idle"
        assert WorkerStatus.WORKING.value == "working"

    def test_all_statuses_exist(self):
        """Should have exactly 2 worker statuses."""
        assert len(WorkerStatus) == 2


class TestGuestStatusEnum:
    """Tests for GuestStatus enum."""

    def test_guest_status_values(self):
        """Guest status should have happy and stressed states."""
        assert GuestStatus.HAPPY.value == "happy"
        assert GuestStatus.STRESSED.value == "stressed"


class TestTeamTypeEnum:
    """Tests for TeamType enum."""

    def test_all_teams_exist(self):
        """Should have all 5 required teams."""
        expected_teams = {"security", "clean_up", "catering", "officiant", "waiters"}
        actual_teams = {t.value for t in TeamType}
        assert actual_teams == expected_teams

    def test_team_count(self):
        """Should have exactly 5 teams."""
        assert len(TeamType) == 5


class TestRoutineTypeEnum:
    """Tests for RoutineType enum."""

    def test_routine_values(self):
        """Routine values should be (working_time, idle_time) tuples."""
        assert RoutineType.STANDARD.value == (20, 5)
        assert RoutineType.INTERMITTENT.value == (5, 5)
        assert RoutineType.CONCENTRATED.value == (60, 60)

    def test_routine_tuple_structure(self):
        """Each routine should be a 2-tuple of integers."""
        for routine in RoutineType:
            assert isinstance(routine.value, tuple)
            assert len(routine.value) == 2
            assert all(isinstance(v, int) for v in routine.value)


class TestTeamRoutinesMapping:
    """Tests for TEAM_ROUTINES mapping."""

    def test_all_teams_have_routines(self):
        """Every team should have an assigned routine."""
        for team in TeamType:
            assert team in TEAM_ROUTINES
            assert isinstance(TEAM_ROUTINES[team], RoutineType)

    def test_specific_team_routines(self):
        """Teams should have their correct routines per spec."""
        assert TEAM_ROUTINES[TeamType.SECURITY] == RoutineType.STANDARD
        assert TEAM_ROUTINES[TeamType.CLEAN_UP] == RoutineType.INTERMITTENT
        assert TEAM_ROUTINES[TeamType.CATERING] == RoutineType.CONCENTRATED
        assert TEAM_ROUTINES[TeamType.OFFICIANT] == RoutineType.CONCENTRATED
        assert TEAM_ROUTINES[TeamType.WAITERS] == RoutineType.STANDARD


class TestTeamEventTypesMapping:
    """Tests for TEAM_EVENT_TYPES mapping."""

    def test_all_teams_have_event_types(self):
        """Every team should handle at least one event type."""
        for team in TeamType:
            assert team in TEAM_EVENT_TYPES
            assert len(TEAM_EVENT_TYPES[team]) > 0

    def test_security_event_types(self):
        """Security should handle brawl, not_on_list, accident."""
        assert TEAM_EVENT_TYPES[TeamType.SECURITY] == {"brawl", "not_on_list", "accident"}

    def test_cleanup_event_types(self):
        """Clean_up should handle dirty_table, broken_items, dirty_floor."""
        assert TEAM_EVENT_TYPES[TeamType.CLEAN_UP] == {"dirty_table", "broken_items", "dirty_floor"}

    def test_catering_event_types(self):
        """Catering should handle bad_food, music, feeling_ill."""
        assert TEAM_EVENT_TYPES[TeamType.CATERING] == {"bad_food", "music", "feeling_ill"}

    def test_officiant_event_types(self):
        """Officiant should handle bride, groom."""
        assert TEAM_EVENT_TYPES[TeamType.OFFICIANT] == {"bride", "groom"}

    def test_waiters_event_types(self):
        """Waiters should handle broken_items, accident, bad_food."""
        assert TEAM_EVENT_TYPES[TeamType.WAITERS] == {"broken_items", "accident", "bad_food"}


class TestEventTypeToTeamsMapping:
    """Tests for EVENT_TYPE_TO_TEAMS reverse mapping."""

    def test_all_event_types_mapped(self):
        """All event types should map to at least one team."""
        all_event_types = set()
        for event_types in TEAM_EVENT_TYPES.values():
            all_event_types.update(event_types)

        for event_type in all_event_types:
            assert event_type in EVENT_TYPE_TO_TEAMS
            assert len(EVENT_TYPE_TO_TEAMS[event_type]) > 0

    def test_shared_event_types(self):
        """Some event types are handled by multiple teams."""
        # broken_items is handled by both Clean_up and Waiters
        assert TeamType.CLEAN_UP in EVENT_TYPE_TO_TEAMS["broken_items"]
        assert TeamType.WAITERS in EVENT_TYPE_TO_TEAMS["broken_items"]

        # accident is handled by both Security and Waiters
        assert TeamType.SECURITY in EVENT_TYPE_TO_TEAMS["accident"]
        assert TeamType.WAITERS in EVENT_TYPE_TO_TEAMS["accident"]

        # bad_food is handled by both Catering and Waiters
        assert TeamType.CATERING in EVENT_TYPE_TO_TEAMS["bad_food"]
        assert TeamType.WAITERS in EVENT_TYPE_TO_TEAMS["bad_food"]

    def test_unique_event_types(self):
        """Some event types are unique to one team."""
        assert EVENT_TYPE_TO_TEAMS["brawl"] == [TeamType.SECURITY]
        assert EVENT_TYPE_TO_TEAMS["bride"] == [TeamType.OFFICIANT]
        assert EVENT_TYPE_TO_TEAMS["groom"] == [TeamType.OFFICIANT]
        assert EVENT_TYPE_TO_TEAMS["music"] == [TeamType.CATERING]


class TestKafkaTopics:
    """Tests for KAFKA_TOPICS configuration."""

    def test_required_topics_exist(self):
        """Should have topics for events, validated, and each team."""
        assert "events" in KAFKA_TOPICS
        assert "validated" in KAFKA_TOPICS

    def test_team_topics_exist(self):
        """Each team should have a Kafka topic."""
        for team in TeamType:
            assert team in KAFKA_TOPICS
            assert isinstance(KAFKA_TOPICS[team], str)

    def test_topic_names_are_strings(self):
        """All topic values should be strings."""
        for key, value in KAFKA_TOPICS.items():
            if isinstance(key, str):  # Skip TeamType keys for this check
                assert isinstance(value, str)
