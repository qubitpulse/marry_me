"""
Configuration constants for the Marry Me wedding simulation.
"""
from enum import Enum
from dataclasses import dataclass


# Priority timeframes (in seconds for simulation)
class Priority(Enum):
    HIGH = 5
    MEDIUM = 10
    LOW = 15


# Worker/Guest status
class WorkerStatus(Enum):
    IDLE = "idle"
    WORKING = "working"


class GuestStatus(Enum):
    HAPPY = "happy"
    STRESSED = "stressed"


# Team types
class TeamType(Enum):
    SECURITY = "security"
    CLEAN_UP = "clean_up"
    CATERING = "catering"
    OFFICIANT = "officiant"
    WAITERS = "waiters"


# Routine types with (working_seconds, idle_seconds)
class RoutineType(Enum):
    STANDARD = (20, 5)
    INTERMITTENT = (5, 5)
    CONCENTRATED = (60, 60)


# Team to Routine mapping
TEAM_ROUTINES = {
    TeamType.SECURITY: RoutineType.STANDARD,
    TeamType.CLEAN_UP: RoutineType.INTERMITTENT,
    TeamType.CATERING: RoutineType.CONCENTRATED,
    TeamType.OFFICIANT: RoutineType.CONCENTRATED,
    TeamType.WAITERS: RoutineType.STANDARD,
}


# Event types each team can handle
TEAM_EVENT_TYPES = {
    TeamType.SECURITY: {"brawl", "not_on_list", "accident"},
    TeamType.CLEAN_UP: {"dirty_table", "broken_items", "dirty_floor"},
    TeamType.CATERING: {"bad_food", "music", "feeling_ill"},
    TeamType.OFFICIANT: {"bride", "groom"},
    TeamType.WAITERS: {"broken_items", "accident", "bad_food"},
}

# Reverse mapping: event_type -> list of teams that can handle it
EVENT_TYPE_TO_TEAMS = {}
for team, event_types in TEAM_EVENT_TYPES.items():
    for event_type in event_types:
        if event_type not in EVENT_TYPE_TO_TEAMS:
            EVENT_TYPE_TO_TEAMS[event_type] = []
        EVENT_TYPE_TO_TEAMS[event_type].append(team)


# Simulation constants
SIMULATION_DURATION_SECONDS = 360  # 6 minutes
EVENT_HANDLING_TIME_SECONDS = 3

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPICS = {
    "events": "wedding-events",
    "validated": "validated-events",
    TeamType.SECURITY: "team-security",
    TeamType.CLEAN_UP: "team-cleanup",
    TeamType.CATERING: "team-catering",
    TeamType.OFFICIANT: "team-officiant",
    TeamType.WAITERS: "team-waiters",
}
