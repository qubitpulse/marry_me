"""
Marry Me Organizer: Distributes validated events to appropriate teams.
"""
import json
import logging
from kafka import KafkaProducer, KafkaConsumer

from config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPICS,
    EVENT_TYPE_TO_TEAMS,
    Priority,
)
from models import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Organizer:
    """
    The Organizer receives validated events and distributes them
    to the appropriate team topics based on event type and priority.
    """

    def __init__(self):
        self.producer = None
        self.consumer = None
        # Priority queues for each team (in-memory buffer for prioritization)
        self.team_queues = {team: [] for team in KAFKA_TOPICS if isinstance(team, type)}

    def connect(self):
        """Initialize Kafka producer and consumer."""
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        self.consumer = KafkaConsumer(
            KAFKA_TOPICS["validated"],
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id="organizer",
            auto_offset_reset="earliest",
        )
        logger.info("Organizer connected to Kafka")

    def get_target_team(self, event: Event):
        """
        Determine which team should handle this event.
        For events that multiple teams can handle, pick the first one.
        """
        teams = EVENT_TYPE_TO_TEAMS.get(event.event_type, [])
        if teams:
            return teams[0]
        return None

    def distribute_event(self, event: Event):
        """Send event to the appropriate team topic."""
        target_team = self.get_target_team(event)

        if target_team is None:
            logger.warning(f"No team found for event type: {event.event_type}")
            return False

        topic = KAFKA_TOPICS[target_team]

        # Use priority as a message header for ordering
        # Kafka doesn't natively support priority queues, but teams can
        # consume and sort by priority
        self.producer.send(
            topic,
            key=event.id,
            value=event.to_dict(),
        )

        logger.info(
            f"Organizer distributed event {event.id} ({event.event_type}) "
            f"to {target_team.value} with priority {event.priority.name}"
        )
        return True

    def run(self):
        """Main loop: consume validated events and distribute to teams."""
        logger.info("Organizer starting...")
        self.connect()

        try:
            for message in self.consumer:
                event_data = message.value
                event = Event.from_dict(event_data)
                self.distribute_event(event)
        except KeyboardInterrupt:
            logger.info("Organizer shutting down...")
        finally:
            self.close()

    def close(self):
        """Clean up resources."""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()


def run_organizer():
    """Entry point for running the organizer as a separate process."""
    organizer = Organizer()
    organizer.run()


if __name__ == "__main__":
    run_organizer()
