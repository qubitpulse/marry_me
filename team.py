"""
Team: Manages workers and processes events for a specific team.
"""
import json
import logging
import time
import heapq
from multiprocessing import Process, Queue, Value
from threading import Thread, Lock
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime

from config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPICS,
    TEAM_ROUTINES,
    EVENT_HANDLING_TIME_SECONDS,
    TeamType,
    Priority,
)
from models import Event, Worker, Team, WorkerStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TeamManager:
    """
    Manages a team of workers, handling the routine cycles
    and distributing events to available workers.
    """

    def __init__(
        self,
        team_type: TeamType,
        num_workers: int,
        stats_queue: Queue,
        simulation_start: Value,
    ):
        self.team_type = team_type
        self.routine = TEAM_ROUTINES[team_type]
        self.working_time, self.idle_time = self.routine.value

        # Create team and workers
        self.team = Team(
            team_type=team_type,
            routine=self.routine,
            workers=[
                Worker(id=f"{team_type.value}-worker-{i}", team=team_type)
                for i in range(num_workers)
            ],
        )

        # Event queue (priority queue based on event priority)
        self.event_queue = []
        self.queue_lock = Lock()

        # Kafka
        self.consumer = None
        self.producer = None

        # Stats reporting
        self.stats_queue = stats_queue
        self.simulation_start = simulation_start

        # Routine state
        self.in_working_phase = True
        self.phase_start_time = 0

        # Control
        self.running = False

    def connect(self):
        """Initialize Kafka consumer and producer."""
        topic = KAFKA_TOPICS[self.team_type]
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id=f"team-{self.team_type.value}",
            auto_offset_reset="earliest",
            consumer_timeout_ms=1000,  # Non-blocking consume
        )
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        logger.info(f"Team {self.team_type.value} connected to Kafka")

    def get_priority_value(self, priority: Priority) -> int:
        """Convert priority to sortable value (lower = higher priority)."""
        return {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}[priority]

    def add_event_to_queue(self, event: Event):
        """Add event to priority queue."""
        with self.queue_lock:
            # heapq uses min-heap, so lower priority value = higher priority
            priority_value = self.get_priority_value(event.priority)
            heapq.heappush(self.event_queue, (priority_value, event.created_at, event))
        logger.debug(f"Team {self.team_type.value} queued event {event.id}")

    def get_next_event(self) -> Event | None:
        """Get highest priority event from queue."""
        with self.queue_lock:
            if self.event_queue:
                _, _, event = heapq.heappop(self.event_queue)
                return event
        return None

    def is_in_idle_phase(self, current_time: float) -> bool:
        """
        Check if team is in idle phase based on routine cycle.
        Workers start in WORKING phase, then cycle.
        """
        if self.simulation_start.value == 0:
            return False

        elapsed = current_time - self.simulation_start.value
        cycle_duration = self.working_time + self.idle_time
        position_in_cycle = elapsed % cycle_duration

        # First part of cycle is working, second part is idle
        return position_in_cycle >= self.working_time

    def handle_event(self, worker: Worker, event: Event):
        """Worker handles an event (takes EVENT_HANDLING_TIME_SECONDS)."""
        worker.status = WorkerStatus.WORKING
        worker.current_event = event

        logger.info(
            f"Worker {worker.id} handling event {event.id} "
            f"({event.event_type}, {event.priority.name})"
        )

        # Simulate handling time
        time.sleep(EVENT_HANDLING_TIME_SECONDS)

        # Mark as handled
        event.handled = True
        event.handled_by = worker.id
        worker.status = WorkerStatus.IDLE
        worker.current_event = None

        # Report to stats
        self.stats_queue.put({"type": "handled", "event": event.to_dict()})

        logger.info(f"Worker {worker.id} completed event {event.id}")

    def check_expired_events(self):
        """Check for and remove expired events from the queue."""
        current_time = time.time()
        with self.queue_lock:
            expired = []
            remaining = []
            for item in self.event_queue:
                priority_val, created_at, event = item
                if event.is_expired(current_time):
                    event.expired = True
                    expired.append(event)
                else:
                    remaining.append(item)

            # Rebuild heap with remaining events
            self.event_queue = remaining
            heapq.heapify(self.event_queue)

            # Report expired events
            for event in expired:
                logger.warning(
                    f"Event {event.id} expired in team {self.team_type.value}"
                )
                self.stats_queue.put({"type": "expired", "event": event.to_dict()})

    def consume_events(self):
        """Thread: Continuously consume events from Kafka."""
        while self.running:
            try:
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=500)
                for topic_partition, records in messages.items():
                    for record in records:
                        event = Event.from_dict(record.value)
                        self.add_event_to_queue(event)
            except Exception as e:
                logger.error(f"Error consuming events: {e}")

    def process_events(self):
        """Thread: Process events from queue when workers are available."""
        while self.running:
            current_time = time.time()

            # Check for expired events periodically
            self.check_expired_events()

            # Check if we're in idle phase (workers can work)
            if not self.is_in_idle_phase(current_time):
                time.sleep(0.1)
                continue

            # Find available workers
            available_workers = self.team.get_available_workers()
            if not available_workers:
                time.sleep(0.1)
                continue

            # Assign events to available workers
            for worker in available_workers:
                event = self.get_next_event()
                if event is None:
                    break

                # Check if event is still valid
                if event.is_expired(current_time):
                    event.expired = True
                    self.stats_queue.put({"type": "expired", "event": event.to_dict()})
                    continue

                # Handle in a separate thread to not block other workers
                Thread(target=self.handle_event, args=(worker, event)).start()

            time.sleep(0.1)

    def run(self):
        """Main entry point for the team manager."""
        logger.info(
            f"Team {self.team_type.value} starting with {len(self.team.workers)} workers "
            f"(routine: {self.working_time}s work, {self.idle_time}s idle)"
        )
        self.connect()
        self.running = True

        # Start consumer and processor threads
        consumer_thread = Thread(target=self.consume_events, daemon=True)
        processor_thread = Thread(target=self.process_events, daemon=True)

        consumer_thread.start()
        processor_thread.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self.close()

    def close(self):
        """Clean up resources."""
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        logger.info(f"Team {self.team_type.value} shut down")


def run_team(
    team_type_value: str,
    num_workers: int,
    stats_queue: Queue,
    simulation_start: Value,
):
    """Entry point for running a team as a separate process."""
    team_type = TeamType(team_type_value)
    manager = TeamManager(team_type, num_workers, stats_queue, simulation_start)
    manager.run()
