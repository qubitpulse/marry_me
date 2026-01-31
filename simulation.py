"""
Wedding Simulation: Main orchestrator for the Marry Me system.
"""
import json
import logging
import time
import random
from multiprocessing import Process, Queue, Value
from ctypes import c_double
from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

from config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPICS,
    SIMULATION_DURATION_SECONDS,
    TEAM_EVENT_TYPES,
    TeamType,
    Priority,
)
from models import Event, SimulationStats
from coordinator import run_coordinator
from organizer import run_organizer
from team import run_team

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Sample event descriptions for generating test events
EVENT_DESCRIPTIONS = {
    "brawl": [
        "Two guests arguing over seating arrangements",
        "Fight broke out near the bar",
        "Uncle Bob and Cousin Jim at it again",
    ],
    "not_on_list": [
        "Unknown person trying to enter",
        "Plus-one not on the guest list",
        "Wedding crasher spotted",
    ],
    "accident": [
        "Guest tripped on the dance floor",
        "Someone bumped into the cake table",
        "Child running and fell",
    ],
    "dirty_table": [
        "Table 5 needs cleaning",
        "Spilled wine on table 12",
        "Dessert plates piling up at table 3",
    ],
    "broken_items": [
        "Champagne glass shattered",
        "Chair leg broken",
        "Decoration fell and broke",
    ],
    "dirty_floor": [
        "Food spilled on dance floor",
        "Muddy footprints in entrance",
        "Someone dropped their cake",
    ],
    "bad_food": [
        "Guest complaining about cold food",
        "Vegetarian got served meat",
        "Food allergy concern",
    ],
    "music": [
        "Music too loud complaints",
        "Request to change the song",
        "Microphone feedback issues",
    ],
    "feeling_ill": [
        "Guest has stomach ache after eating",
        "Someone feeling dizzy",
        "Guest needs medical attention",
    ],
    "bride": [
        "Bride needs assistance with dress",
        "Bride requesting water",
        "Bride ready for ceremony",
    ],
    "groom": [
        "Groom can't find the rings",
        "Groom needs help with tie",
        "Groom ready for ceremony",
    ],
}


class WeddingSimulation:
    """
    Orchestrates the entire wedding simulation.
    """

    def __init__(
        self,
        num_coordinators: int = 2,
        workers_per_team: int = 3,
        events_file: str = None,
    ):
        self.num_coordinators = num_coordinators
        self.workers_per_team = workers_per_team
        self.events_file = events_file

        # Processes
        self.processes = []

        # Shared state
        self.stats_queue = Queue()
        self.simulation_start = Value(c_double, 0.0)

        # Statistics
        self.stats = SimulationStats()

        # Kafka producer for injecting events
        self.producer = None

    def setup_kafka_topics(self):
        """Create necessary Kafka topics if they don't exist."""
        try:
            admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
            topics = [
                NewTopic(name=topic, num_partitions=3, replication_factor=1)
                for topic in KAFKA_TOPICS.values()
                if isinstance(topic, str)
            ]
            admin.create_topics(topics)
            logger.info("Kafka topics created")
        except TopicAlreadyExistsError:
            logger.info("Kafka topics already exist")
        except Exception as e:
            logger.warning(f"Could not create topics (may already exist): {e}")

    def start_processes(self):
        """Start all component processes."""
        # Start coordinators
        for i in range(self.num_coordinators):
            p = Process(target=run_coordinator, args=(f"coord-{i}",))
            p.start()
            self.processes.append(("coordinator", p))
            logger.info(f"Started coordinator {i}")

        # Start organizer
        p = Process(target=run_organizer)
        p.start()
        self.processes.append(("organizer", p))
        logger.info("Started organizer")

        # Start teams
        for team_type in TeamType:
            p = Process(
                target=run_team,
                args=(
                    team_type.value,
                    self.workers_per_team,
                    self.stats_queue,
                    self.simulation_start,
                ),
            )
            p.start()
            self.processes.append((f"team-{team_type.value}", p))
            logger.info(f"Started team {team_type.value}")

        # Give processes time to initialize
        time.sleep(2)

    def stop_processes(self):
        """Stop all component processes."""
        for name, process in self.processes:
            process.terminate()
            process.join(timeout=5)
            logger.info(f"Stopped {name}")
        self.processes.clear()

    def generate_random_event(self, wedding_time: str) -> Event:
        """Generate a random event for testing."""
        # Pick random event type
        all_event_types = list(EVENT_DESCRIPTIONS.keys())
        event_type = random.choice(all_event_types)

        # Pick random priority (weighted towards medium/low)
        priority = random.choices(
            [Priority.HIGH, Priority.MEDIUM, Priority.LOW],
            weights=[0.2, 0.5, 0.3],
        )[0]

        # Pick random description
        description = random.choice(EVENT_DESCRIPTIONS[event_type])

        return Event(
            event_type=event_type,
            priority=priority,
            description=description,
            timestamp=wedding_time,
        )

    def load_events_from_file(self, filepath: str) -> list[dict]:
        """Load events from a JSON file, normalizing external dataset formats."""
        with open(filepath, "r") as f:
            raw_events = json.load(f)

        normalized = []
        for event_data in raw_events:
            normalized.append(self._normalize_event_data(event_data))
        return normalized

    @staticmethod
    def _normalize_event_data(event_data: dict) -> dict:
        """Normalize event data from external datasets (e.g. QwasarSV format)."""
        data = dict(event_data)

        # Normalize priority: "High" -> "HIGH", "Medium" -> "MEDIUM", etc.
        if "priority" in data:
            data["priority"] = data["priority"].upper()

        # Fix known typos from reference datasets
        if data.get("event_type") == "broken_itens":
            data["event_type"] = "broken_items"

        # Ensure id is a string
        if "id" in data:
            data["id"] = str(data["id"])

        # Provide defaults for fields absent in external datasets
        if "created_at" not in data:
            data["created_at"] = 0
        if "handled" not in data:
            data["handled"] = False
        if "expired" not in data:
            data["expired"] = False

        return data

    def inject_event(self, event: Event):
        """Send an event to the system."""
        if not self.producer:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )

        self.producer.send(
            KAFKA_TOPICS["events"],
            key=event.id,
            value=event.to_dict(),
        )
        self.stats.total_events += 1
        logger.info(
            f"Injected event {event.id}: {event.event_type} "
            f"({event.priority.name}) at {event.timestamp}"
        )

    def collect_stats(self):
        """Collect statistics from the stats queue."""
        while not self.stats_queue.empty():
            try:
                stat = self.stats_queue.get_nowait()
                if stat["type"] == "handled":
                    self.stats.handled_events += 1
                elif stat["type"] == "expired":
                    self.stats.expired_events += 1
                    self.stats.stress_level += 1
            except Exception:
                break

    def simulation_time_to_wedding_time(self, elapsed_seconds: float) -> str:
        """Convert simulation time to wedding time (HH:MM format)."""
        # 1 simulation second = 1 wedding minute
        total_minutes = int(elapsed_seconds)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def run(self, event_rate: float = 0.5):
        """
        Run the wedding simulation.

        Args:
            event_rate: Average events per second to generate (for random mode)
        """
        logger.info("=" * 60)
        logger.info("WEDDING SIMULATION STARTING")
        logger.info("=" * 60)

        # Setup
        self.setup_kafka_topics()
        self.start_processes()

        # Record simulation start
        self.simulation_start.value = time.time()
        start_time = self.simulation_start.value

        try:
            if self.events_file:
                # Load and inject events from file
                events = self.load_events_from_file(self.events_file)
                for event_data in events:
                    event = Event.from_dict(event_data)
                    self.inject_event(event)
                    time.sleep(0.1)  # Small delay between injections
            else:
                # Generate random events throughout simulation
                last_event_time = start_time
                while time.time() - start_time < SIMULATION_DURATION_SECONDS:
                    current_time = time.time()
                    elapsed = current_time - start_time

                    # Generate events based on rate
                    if random.random() < event_rate:
                        wedding_time = self.simulation_time_to_wedding_time(elapsed)
                        event = self.generate_random_event(wedding_time)
                        self.inject_event(event)

                    # Collect stats periodically
                    self.collect_stats()

                    # Log progress every 30 seconds
                    if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                        wedding_time = self.simulation_time_to_wedding_time(elapsed)
                        logger.info(
                            f"Simulation progress: {wedding_time} "
                            f"(Events: {self.stats.total_events}, "
                            f"Handled: {self.stats.handled_events}, "
                            f"Stress: {self.stats.stress_level})"
                        )

                    time.sleep(1)

            # Wait for remaining events to be processed
            logger.info("Waiting for remaining events to be processed...")
            time.sleep(20)  # Allow time for queue to drain

            # Final stats collection
            self.collect_stats()

        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        finally:
            self.stop_processes()
            if self.producer:
                self.producer.close()

        # Print final results
        self.print_results()

    def print_results(self):
        """Print final simulation results."""
        logger.info("=" * 60)
        logger.info("WEDDING SIMULATION COMPLETE")
        logger.info("=" * 60)
        results = self.stats.to_dict()
        for key, value in results.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 60)

        # Return for programmatic use
        return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Marry Me Wedding Simulation")
    parser.add_argument(
        "--coordinators",
        type=int,
        default=2,
        help="Number of coordinators",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Workers per team",
    )
    parser.add_argument(
        "--events-file",
        type=str,
        help="JSON file with predefined events",
    )
    parser.add_argument(
        "--event-rate",
        type=float,
        default=0.5,
        help="Events per second (random mode)",
    )

    args = parser.parse_args()

    simulation = WeddingSimulation(
        num_coordinators=args.coordinators,
        workers_per_team=args.workers,
        events_file=args.events_file,
    )
    simulation.run(event_rate=args.event_rate)


if __name__ == "__main__":
    main()
