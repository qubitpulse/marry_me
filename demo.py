#!/usr/bin/env python3
"""
Marry Me - Wedding Event Management Demo

A standalone demonstration of the wedding event management system.
Runs without Kafka, using in-memory queues for easy demonstration.

Usage:
    python demo.py                    # Run with defaults
    python demo.py --duration 30      # Run for 30 seconds
    python demo.py --workers 5        # 5 workers per team
    python demo.py --speed 2          # 2x speed
"""

import argparse
import os
import queue
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

# ============================================================================
# Configuration
# ============================================================================

class Priority(Enum):
    HIGH = 5
    MEDIUM = 10
    LOW = 15


class TeamType(Enum):
    SECURITY = "Security"
    CLEAN_UP = "Clean Up"
    CATERING = "Catering"
    OFFICIANT = "Officiant"
    WAITERS = "Waiters"


class RoutineType(Enum):
    STANDARD = (20, 5)       # 20s work, 5s idle
    INTERMITTENT = (5, 5)    # 5s work, 5s idle
    CONCENTRATED = (60, 60)  # 60s work, 60s idle


TEAM_ROUTINES = {
    TeamType.SECURITY: RoutineType.STANDARD,
    TeamType.CLEAN_UP: RoutineType.INTERMITTENT,
    TeamType.CATERING: RoutineType.CONCENTRATED,
    TeamType.OFFICIANT: RoutineType.CONCENTRATED,
    TeamType.WAITERS: RoutineType.STANDARD,
}

TEAM_EVENT_TYPES = {
    TeamType.SECURITY: {"brawl", "not_on_list", "accident"},
    TeamType.CLEAN_UP: {"dirty_table", "broken_items", "dirty_floor"},
    TeamType.CATERING: {"bad_food", "music", "feeling_ill"},
    TeamType.OFFICIANT: {"bride", "groom"},
    TeamType.WAITERS: {"broken_items", "accident", "bad_food"},
}

EVENT_TYPE_TO_TEAM = {}
for team, types in TEAM_EVENT_TYPES.items():
    for t in types:
        if t not in EVENT_TYPE_TO_TEAM:
            EVENT_TYPE_TO_TEAM[t] = team

EVENT_DESCRIPTIONS = {
    "brawl": ["Fight at the bar", "Guests arguing loudly", "Uncle vs Cousin"],
    "not_on_list": ["Uninvited guest", "Plus-one not listed", "Wedding crasher"],
    "accident": ["Guest tripped", "Someone bumped the cake", "Child fell down"],
    "dirty_table": ["Table 5 needs cleaning", "Wine spilled on table", "Plates piling up"],
    "broken_items": ["Glass shattered", "Chair broke", "Decoration fell"],
    "dirty_floor": ["Food on dance floor", "Muddy footprints", "Cake dropped"],
    "bad_food": ["Cold appetizers", "Wrong dietary meal", "Food complaint"],
    "music": ["Music too loud", "Song request", "Microphone feedback"],
    "feeling_ill": ["Guest dizzy", "Stomach ache", "Needs medical help"],
    "bride": ["Dress assistance", "Bride needs water", "Bride ready"],
    "groom": ["Can't find rings", "Tie help needed", "Groom ready"],
}

TEAM_COLORS = {
    TeamType.SECURITY: "\033[91m",    # Red
    TeamType.CLEAN_UP: "\033[93m",    # Yellow
    TeamType.CATERING: "\033[92m",    # Green
    TeamType.OFFICIANT: "\033[95m",   # Magenta
    TeamType.WAITERS: "\033[96m",     # Cyan
}

PRIORITY_COLORS = {
    Priority.HIGH: "\033[91m",        # Red
    Priority.MEDIUM: "\033[93m",      # Yellow
    Priority.LOW: "\033[92m",         # Green
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Event:
    id: str
    event_type: str
    priority: Priority
    description: str
    timestamp: str
    created_at: float = field(default_factory=time.time)
    handled: bool = False
    handled_by: Optional[str] = None
    expired: bool = False

    def time_remaining(self, current_time: float, speed: float = 1.0) -> float:
        deadline = self.created_at + (self.priority.value / speed)
        return max(0, deadline - current_time)

    def is_expired(self, current_time: float, speed: float = 1.0) -> bool:
        return self.time_remaining(current_time, speed) <= 0


@dataclass
class Worker:
    id: str
    team: TeamType
    busy: bool = False
    current_event: Optional[Event] = None


# ============================================================================
# Demo Simulation
# ============================================================================

class WeddingDemo:
    """Interactive wedding event management demonstration."""

    def __init__(
        self,
        duration: int = 60,
        workers_per_team: int = 3,
        event_rate: float = 0.8,
        speed: float = 1.0,
    ):
        self.duration = duration
        self.workers_per_team = workers_per_team
        self.event_rate = event_rate
        self.speed = speed

        # State
        self.running = False
        self.start_time = 0
        self.event_counter = 0

        # Queues
        self.event_queue = queue.Queue()
        self.team_queues = {team: queue.PriorityQueue() for team in TeamType}

        # Workers
        self.workers = {
            team: [Worker(f"{team.value[:3]}-{i+1}", team) for i in range(workers_per_team)]
            for team in TeamType
        }

        # Statistics
        self.stats = {
            "total": 0,
            "handled": 0,
            "expired": 0,
            "by_team": {team: {"handled": 0, "expired": 0} for team in TeamType},
            "by_priority": {p: {"handled": 0, "expired": 0} for p in Priority},
        }

        # Activity log (recent events for display)
        self.activity_log = []
        self.log_lock = threading.Lock()

    def log_activity(self, message: str, color: str = ""):
        """Add an activity to the log."""
        with self.log_lock:
            timestamp = time.strftime("%H:%M:%S")
            self.activity_log.append(f"{DIM}[{timestamp}]{RESET} {color}{message}{RESET}")
            if len(self.activity_log) > 8:
                self.activity_log.pop(0)

    def generate_event(self) -> Event:
        """Generate a random wedding event."""
        self.event_counter += 1
        event_type = random.choice(list(EVENT_DESCRIPTIONS.keys()))
        priority = random.choices(
            [Priority.HIGH, Priority.MEDIUM, Priority.LOW],
            weights=[0.2, 0.5, 0.3],
        )[0]
        description = random.choice(EVENT_DESCRIPTIONS[event_type])

        elapsed = time.time() - self.start_time
        wedding_minutes = int(elapsed * self.speed)
        wedding_time = f"{wedding_minutes // 60:02d}:{wedding_minutes % 60:02d}"

        return Event(
            id=f"E{self.event_counter:04d}",
            event_type=event_type,
            priority=priority,
            description=description,
            timestamp=wedding_time,
        )

    def get_team_for_event(self, event: Event) -> TeamType:
        """Determine which team handles an event."""
        return EVENT_TYPE_TO_TEAM.get(event.event_type, TeamType.WAITERS)

    def is_team_in_idle_phase(self, team: TeamType) -> bool:
        """Check if team is in idle phase (can work)."""
        routine = TEAM_ROUTINES[team]
        work_time, idle_time = routine.value
        work_time /= self.speed
        idle_time /= self.speed
        cycle = work_time + idle_time
        elapsed = time.time() - self.start_time
        position = elapsed % cycle
        return position >= work_time

    def event_generator(self):
        """Thread: Generate events periodically."""
        while self.running:
            if random.random() < self.event_rate:
                event = self.generate_event()
                self.stats["total"] += 1
                team = self.get_team_for_event(event)
                priority_val = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}[event.priority]
                self.team_queues[team].put((priority_val, event.created_at, event))

                color = PRIORITY_COLORS[event.priority]
                self.log_activity(
                    f"NEW {event.id} [{event.priority.name}] {event.event_type} -> {team.value}",
                    color
                )
            time.sleep(1 / self.speed)

    def team_processor(self, team: TeamType):
        """Thread: Process events for a specific team."""
        while self.running:
            # Check if in idle phase (workers available)
            if not self.is_team_in_idle_phase(team):
                time.sleep(0.1)
                continue

            # Find available worker
            available = [w for w in self.workers[team] if not w.busy]
            if not available:
                time.sleep(0.1)
                continue

            # Get highest priority event
            try:
                _, _, event = self.team_queues[team].get_nowait()
            except queue.Empty:
                time.sleep(0.1)
                continue

            # Check if expired
            current_time = time.time()
            if event.is_expired(current_time, self.speed):
                event.expired = True
                self.stats["expired"] += 1
                self.stats["by_team"][team]["expired"] += 1
                self.stats["by_priority"][event.priority]["expired"] += 1
                self.log_activity(
                    f"EXPIRED {event.id} [{event.priority.name}] {event.event_type}",
                    "\033[91m"  # Red
                )
                continue

            # Assign to worker
            worker = available[0]
            worker.busy = True
            worker.current_event = event

            color = TEAM_COLORS[team]
            self.log_activity(
                f"HANDLING {event.id} by {worker.id}",
                color
            )

            # Simulate handling (3 seconds / speed)
            time.sleep(3 / self.speed)

            # Complete
            event.handled = True
            event.handled_by = worker.id
            worker.busy = False
            worker.current_event = None

            self.stats["handled"] += 1
            self.stats["by_team"][team]["handled"] += 1
            self.stats["by_priority"][event.priority]["handled"] += 1

            self.log_activity(
                f"DONE {event.id} by {worker.id}",
                color
            )

    def expiry_checker(self):
        """Thread: Check for expired events in queues."""
        while self.running:
            current_time = time.time()
            for team in TeamType:
                expired_events = []
                remaining_events = []

                # Drain and check queue
                while True:
                    try:
                        item = self.team_queues[team].get_nowait()
                        _, _, event = item
                        if event.is_expired(current_time, self.speed):
                            expired_events.append(event)
                        else:
                            remaining_events.append(item)
                    except queue.Empty:
                        break

                # Put back non-expired events
                for item in remaining_events:
                    self.team_queues[team].put(item)

                # Log expired
                for event in expired_events:
                    event.expired = True
                    self.stats["expired"] += 1
                    self.stats["by_team"][team]["expired"] += 1
                    self.stats["by_priority"][event.priority]["expired"] += 1
                    self.log_activity(
                        f"EXPIRED {event.id} [{event.priority.name}] in {team.value} queue",
                        "\033[91m"
                    )

            time.sleep(0.5)

    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def render_progress_bar(self, value: int, max_value: int, width: int = 20) -> str:
        """Render a simple progress bar."""
        if max_value == 0:
            return "[" + " " * width + "]"
        filled = int(width * value / max_value)
        return "[" + "=" * filled + " " * (width - filled) + "]"

    def render_team_status(self, team: TeamType) -> str:
        """Render status line for a team."""
        color = TEAM_COLORS[team]
        routine = TEAM_ROUTINES[team]
        in_idle = self.is_team_in_idle_phase(team)
        phase = f"{BOLD}READY{RESET}" if in_idle else f"{DIM}BUSY{RESET} "

        workers = self.workers[team]
        busy_count = sum(1 for w in workers if w.busy)
        worker_status = f"{busy_count}/{len(workers)} working"

        queue_size = self.team_queues[team].qsize()
        handled = self.stats["by_team"][team]["handled"]
        expired = self.stats["by_team"][team]["expired"]

        return (
            f"{color}{team.value:10}{RESET} "
            f"{phase} | "
            f"Workers: {worker_status:12} | "
            f"Queue: {queue_size:3} | "
            f"Done: {handled:3} | "
            f"Expired: {expired:3}"
        )

    def render_display(self):
        """Render the main display."""
        self.clear_screen()

        elapsed = time.time() - self.start_time
        remaining = max(0, self.duration - elapsed)
        wedding_minutes = int(elapsed * self.speed)
        wedding_time = f"{wedding_minutes // 60:02d}:{wedding_minutes % 60:02d}"

        # Header
        print(f"{BOLD}{'=' * 70}{RESET}")
        print(f"{BOLD}           MARRY ME - Wedding Event Management Demo{RESET}")
        print(f"{BOLD}{'=' * 70}{RESET}")
        print()

        # Time info
        progress = min(1.0, elapsed / self.duration)
        bar = self.render_progress_bar(int(progress * 100), 100, 30)
        print(f"  Wedding Time: {BOLD}{wedding_time}{RESET}  |  "
              f"Real Time: {int(elapsed)}s / {self.duration}s  {bar}")
        print()

        # Statistics
        total = self.stats["total"]
        handled = self.stats["handled"]
        expired = self.stats["expired"]
        pending = total - handled - expired
        success_rate = f"{handled/total*100:.1f}%" if total > 0 else "N/A"

        stress_indicator = ""
        if expired == 0:
            stress_indicator = f"\033[92m[Stress: LOW]{RESET}"
        elif expired < 5:
            stress_indicator = f"\033[93m[Stress: MEDIUM]{RESET}"
        else:
            stress_indicator = f"\033[91m[Stress: HIGH]{RESET}"

        print(f"  {BOLD}Statistics:{RESET}")
        print(f"    Total Events: {total:4}  |  Handled: {handled:4}  |  "
              f"Expired: {expired:4}  |  Pending: {pending:4}")
        print(f"    Success Rate: {success_rate:6}  {stress_indicator}")
        print()

        # Priority breakdown
        print(f"  {BOLD}By Priority:{RESET}")
        for p in Priority:
            color = PRIORITY_COLORS[p]
            h = self.stats["by_priority"][p]["handled"]
            e = self.stats["by_priority"][p]["expired"]
            print(f"    {color}{p.name:8}{RESET}: Handled {h:3}, Expired {e:3}")
        print()

        # Team status
        print(f"  {BOLD}Team Status:{RESET}")
        print(f"  {'-' * 66}")
        for team in TeamType:
            print(f"  {self.render_team_status(team)}")
        print(f"  {'-' * 66}")
        print()

        # Activity log
        print(f"  {BOLD}Recent Activity:{RESET}")
        with self.log_lock:
            if self.activity_log:
                for entry in self.activity_log[-6:]:
                    print(f"    {entry}")
            else:
                print(f"    {DIM}Waiting for events...{RESET}")
        print()

        # Footer
        print(f"{DIM}  Press Ctrl+C to stop the demo{RESET}")

    def run(self):
        """Run the demo simulation."""
        self.running = True
        self.start_time = time.time()

        # Start threads
        threads = []

        # Event generator
        t = threading.Thread(target=self.event_generator, daemon=True)
        t.start()
        threads.append(t)

        # Team processors
        for team in TeamType:
            t = threading.Thread(target=self.team_processor, args=(team,), daemon=True)
            t.start()
            threads.append(t)

        # Expiry checker
        t = threading.Thread(target=self.expiry_checker, daemon=True)
        t.start()
        threads.append(t)

        # Main display loop
        try:
            while self.running and (time.time() - self.start_time) < self.duration:
                self.render_display()
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False

        # Final display
        self.render_display()
        self.print_final_report()

    def print_final_report(self):
        """Print final simulation report."""
        print()
        print(f"{BOLD}{'=' * 70}{RESET}")
        print(f"{BOLD}                    SIMULATION COMPLETE{RESET}")
        print(f"{BOLD}{'=' * 70}{RESET}")
        print()

        total = self.stats["total"]
        handled = self.stats["handled"]
        expired = self.stats["expired"]

        print(f"  {BOLD}Final Results:{RESET}")
        print(f"    Total Events Generated:  {total}")
        print(f"    Events Handled:          {handled}")
        print(f"    Events Expired:          {expired}")
        print(f"    Success Rate:            {handled/total*100:.1f}%" if total > 0 else "    Success Rate: N/A")
        print(f"    {BOLD}Stress Level:            {expired}{RESET}")
        print()

        print(f"  {BOLD}Team Performance:{RESET}")
        for team in TeamType:
            color = TEAM_COLORS[team]
            h = self.stats["by_team"][team]["handled"]
            e = self.stats["by_team"][team]["expired"]
            total_team = h + e
            rate = f"{h/total_team*100:.0f}%" if total_team > 0 else "N/A"
            print(f"    {color}{team.value:10}{RESET}: {h:3} handled, {e:3} expired ({rate} success)")
        print()

        # Recommendations
        print(f"  {BOLD}Analysis:{RESET}")
        worst_team = max(
            TeamType,
            key=lambda t: self.stats["by_team"][t]["expired"]
        )
        if self.stats["by_team"][worst_team]["expired"] > 0:
            print(f"    - {worst_team.value} team had the most expired events")
            print(f"      Consider adding more workers or adjusting their routine")

        worst_priority = max(
            Priority,
            key=lambda p: self.stats["by_priority"][p]["expired"]
        )
        if self.stats["by_priority"][worst_priority]["expired"] > 0:
            print(f"    - {worst_priority.name} priority events had highest expiration rate")

        if expired == 0:
            print(f"    {BOLD}\033[92mPerfect score! All events handled on time!{RESET}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Marry Me - Wedding Event Management Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo.py                    # Run with defaults (60s)
  python demo.py --duration 30      # Run for 30 seconds
  python demo.py --workers 5        # 5 workers per team
  python demo.py --speed 2          # 2x speed (faster simulation)
  python demo.py --rate 1.5         # More events per second
        """
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=60,
        help="Simulation duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=3,
        help="Workers per team (default: 3)"
    )
    parser.add_argument(
        "--rate", "-r",
        type=float,
        default=0.8,
        help="Event generation rate (default: 0.8 events/second)"
    )
    parser.add_argument(
        "--speed", "-s",
        type=float,
        default=1.0,
        help="Simulation speed multiplier (default: 1.0)"
    )

    args = parser.parse_args()

    print(f"\n{BOLD}Starting Marry Me Demo...{RESET}")
    print(f"  Duration: {args.duration}s")
    print(f"  Workers per team: {args.workers}")
    print(f"  Event rate: {args.rate}/s")
    print(f"  Speed: {args.speed}x")
    print()
    time.sleep(2)

    demo = WeddingDemo(
        duration=args.duration,
        workers_per_team=args.workers,
        event_rate=args.rate,
        speed=args.speed,
    )
    demo.run()


if __name__ == "__main__":
    main()
