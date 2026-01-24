"""
Coordinator: Receives events, validates them, and sends to the organizer.
"""
import json
import logging
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

from config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPICS,
    EVENT_TYPE_TO_TEAMS,
)
from models import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Coordinator:
    """
    The Coordinator is the entry point of the application.
    It receives events, validates them, and forwards them to the Organizer.
    """

    def __init__(self, coordinator_id: str):
        self.coordinator_id = coordinator_id
        self.producer = None
        self.consumer = None

    def connect(self):
        """Initialize Kafka producer and consumer."""
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        self.consumer = KafkaConsumer(
            KAFKA_TOPICS["events"],
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id=f"coordinator-{self.coordinator_id}",
            auto_offset_reset="earliest",
        )
        logger.info(f"Coordinator {self.coordinator_id} connected to Kafka")

    def validate_event(self, event_data: dict) -> tuple[bool, str]:
        """
        Validate an incoming event.
        Returns (is_valid, error_message).
        """
        required_fields = ["event_type", "priority", "description", "timestamp"]

        # Check required fields
        for field in required_fields:
            if field not in event_data:
                return False, f"Missing required field: {field}"

        # Check if event_type is recognized
        event_type = event_data["event_type"]
        if event_type not in EVENT_TYPE_TO_TEAMS:
            return False, f"Unknown event type: {event_type}"

        # Check if priority is valid
        priority = event_data["priority"]
        if priority not in ["HIGH", "MEDIUM", "LOW"]:
            return False, f"Invalid priority: {priority}"

        # Validate timestamp format (HH:MM)
        timestamp = event_data["timestamp"]
        try:
            hours, minutes = timestamp.split(":")
            hours, minutes = int(hours), int(minutes)
            if not (0 <= hours <= 6 and 0 <= minutes <= 59):
                return False, f"Invalid timestamp: {timestamp}"
        except (ValueError, AttributeError):
            return False, f"Invalid timestamp format: {timestamp}"

        return True, ""

    def route_event(self, event: Event) -> list[str]:
        """
        Determine which team topic(s) to send the event to.
        Returns list of topic names.
        """
        teams = EVENT_TYPE_TO_TEAMS.get(event.event_type, [])
        # For now, send to the first team that can handle it
        # Could be extended to load-balance across multiple teams
        if teams:
            return [KAFKA_TOPICS[teams[0]]]
        return []

    def process_event(self, event_data: dict) -> bool:
        """
        Process a single event: validate and forward to organizer.
        Returns True if event was successfully processed.
        """
        # Validate
        is_valid, error = self.validate_event(event_data)
        if not is_valid:
            logger.warning(
                f"Coordinator {self.coordinator_id} rejected event: {error}"
            )
            return False

        # Create Event object
        event = Event.from_dict(event_data)
        logger.info(
            f"Coordinator {self.coordinator_id} validated event {event.id}: "
            f"{event.event_type} ({event.priority.name})"
        )

        # Forward to validated events topic (for the organizer)
        self.producer.send(
            KAFKA_TOPICS["validated"],
            key=event.id,
            value=event.to_dict(),
        )

        return True

    def run(self):
        """Main loop: consume and process events."""
        logger.info(f"Coordinator {self.coordinator_id} starting...")
        self.connect()

        try:
            for message in self.consumer:
                event_data = message.value
                self.process_event(event_data)
        except KeyboardInterrupt:
            logger.info(f"Coordinator {self.coordinator_id} shutting down...")
        finally:
            self.close()

    def close(self):
        """Clean up resources."""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()


def run_coordinator(coordinator_id: str):
    """Entry point for running a coordinator as a separate process."""
    coordinator = Coordinator(coordinator_id)
    coordinator.run()


if __name__ == "__main__":
    run_coordinator("coordinator-1")
