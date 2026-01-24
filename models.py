"""
Data models for the Marry Me wedding simulation.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid

from config import Priority, WorkerStatus, TeamType, RoutineType


@dataclass
class Event:
    """Represents a wedding event that needs to be handled."""
    event_type: str
    priority: Priority
    description: str
    timestamp: str  # Format: "HH:MM" (wedding time, 00:00 to 06:00)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    handled: bool = False
    handled_by: Optional[str] = None
    expired: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "priority": self.priority.name,
            "description": self.description,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "handled": self.handled,
            "handled_by": self.handled_by,
            "expired": self.expired,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        return cls(
            id=data["id"],
            event_type=data["event_type"],
            priority=Priority[data["priority"]],
            description=data["description"],
            timestamp=data["timestamp"],
            created_at=data["created_at"],
            handled=data.get("handled", False),
            handled_by=data.get("handled_by"),
            expired=data.get("expired", False),
        )

    def time_remaining(self, current_time: float) -> float:
        """Returns seconds remaining before this event expires."""
        deadline = self.created_at + self.priority.value
        return max(0, deadline - current_time)

    def is_expired(self, current_time: float) -> bool:
        """Check if the event has expired based on its priority timeout."""
        return self.time_remaining(current_time) <= 0


@dataclass
class Worker:
    """Represents a worker who handles events."""
    id: str
    team: TeamType
    status: WorkerStatus = WorkerStatus.IDLE
    current_event: Optional[Event] = None

    def is_available(self) -> bool:
        return self.status == WorkerStatus.IDLE


@dataclass
class Team:
    """Represents a team of workers."""
    team_type: TeamType
    routine: RoutineType
    workers: list[Worker] = field(default_factory=list)

    @property
    def working_time(self) -> int:
        return self.routine.value[0]

    @property
    def idle_time(self) -> int:
        return self.routine.value[1]

    def get_available_workers(self) -> list[Worker]:
        return [w for w in self.workers if w.is_available()]


@dataclass
class SimulationStats:
    """Tracks statistics for a wedding simulation."""
    total_events: int = 0
    handled_events: int = 0
    expired_events: int = 0
    stress_level: int = 0  # Incremented for each expired event

    def to_dict(self) -> dict:
        return {
            "total_events": self.total_events,
            "handled_events": self.handled_events,
            "expired_events": self.expired_events,
            "stress_level": self.stress_level,
            "success_rate": (
                f"{(self.handled_events / self.total_events * 100):.1f}%"
                if self.total_events > 0 else "N/A"
            ),
        }
