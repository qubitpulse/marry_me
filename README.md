# Marry Me - Wedding Event Management System
https://github.com/QwasarSV/eng_labs_marry_me

An event-driven application for managing wedding events using Apache Kafka and Python multiprocessing. Built as part of the Qwasar Master's of Science in Computer Science program.

## Quick Start

```bash
# 1. Clone and set up
git clone https://github.com/QwasarSV/eng_labs_marry_me.git
cd eng_labs_marry_me
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Run tests (no Kafka needed)
pytest

# 3. Run the demo (no Kafka needed)
python demo.py --duration 30

# 4. Run the full simulation (requires Docker)
docker-compose up -d       # start Kafka — wait ~30s for startup
python simulation.py       # 6-minute wedding simulation
docker-compose down        # stop Kafka when done
```

Open http://localhost:8080 while the simulation runs to monitor Kafka topics in the browser.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Event Types](#event-types)
- [Timing Rules](#timing-rules)
- [Monitoring and Logging](#monitoring-and-logging)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **Marry Me** system is designed to handle events during a wedding ceremony, routing them to appropriate teams (Security, Clean Up, Catering, Officiant, Waiters) based on event type and priority. The goal is to minimize "stress levels" by ensuring events are handled before their deadlines expire.

### Key Features

- **Event-Driven Architecture**: Uses Apache Kafka for message brokering
- **Multiprocessing**: Each team runs as a separate process for true parallelism
- **Priority Queuing**: HIGH priority events are handled before MEDIUM and LOW
- **Worker Routines**: Teams follow work/idle cycles based on their routine type
- **Stress Tracking**: Monitors expired events and calculates overall stress level
- **Comprehensive Logging**: All events are logged for post-simulation analysis

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PUBLISHERS                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │
│  │ Coordinator │  │ Coordinator │  │ Coordinator │  (Validate & Forward)    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                          │
└─────────┼────────────────┼────────────────┼─────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               BROKER                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Marry Me Organizer                              │    │
│  │                   (Route by Type & Priority)                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ├──────────────┬──────────────┬──────────────┬──────────────┐
          ▼              ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SUBSCRIBERS                                       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ Security │   │ Clean Up │   │ Catering │   │ Officiant│   │ Waiters  │  │
│  │  Team    │   │  Team    │   │  Team    │   │  Team    │   │  Team    │  │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘  │
└───────┼──────────────┼──────────────┼──────────────┼──────────────┼────────┘
        │              │              │              │              │
┌───────┼──────────────┼──────────────┼──────────────┼──────────────┼────────┐
│       ▼              ▼              ▼              ▼              ▼        │
│                              HANDLERS                                       │
│    [W] [W]        [W] [W]       [W] [W]        [W] [W]        [W] [W]      │
│    Workers        Workers       Workers        Workers        Workers      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Docker** and **Docker Compose** (for Kafka)
- **Python 3.10+**
- **pip** (Python package manager)

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker-compose --version

# Check Python
python3 --version
```

---

## Installation

### 1. Clone the Project

```bash
git clone https://github.com/QwasarSV/eng_labs_marry_me.git
cd eng_labs_marry_me
```

### 2. Create a Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## Apache Kafka Setup (Docker)

### What is Kafka?

Apache Kafka is a distributed message broker that enables event-driven communication between components. In this project:

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│ Coordinator │──publish─▶│    Kafka    │◀─consume──│    Team     │
│  (Producer) │         │   (Broker)  │         │  (Consumer) │
└─────────────┘         └─────────────┘         └─────────────┘
```

- **Producers** send messages to **topics**
- **Consumers** subscribe to topics and process messages
- **Topics** are like channels/queues that hold messages

### Kafka Topics in This Project

| Topic | Purpose |
|-------|---------|
| `wedding-events` | Raw events from simulation |
| `validated-events` | Events validated by coordinators |
| `team-security` | Events for Security team |
| `team-cleanup` | Events for Clean Up team |
| `team-catering` | Events for Catering team |
| `team-officiant` | Events for Officiant team |
| `team-waiters` | Events for Waiters team |

### Docker Compose Services

The `docker-compose.yml` starts three containers:

```yaml
┌─────────────────────────────────────────────────────────────┐
│                     Docker Containers                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Zookeeper  │    │    Kafka    │    │  Kafka UI   │     │
│  │  Port 2181  │◀───│  Port 9092  │    │  Port 8080  │     │
│  │             │    │             │    │  (Web GUI)  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

| Service | Port | Purpose |
|---------|------|---------|
| **Zookeeper** | 2181 | Kafka cluster coordination |
| **Kafka** | 9092 | Message broker |
| **Kafka UI** | 8080 | Web interface to view topics/messages |

### Start Kafka

```bash
# Start all containers in background
docker-compose up -d

# View startup logs
docker-compose logs -f

# Check all containers are running
docker-compose ps
```

Expected output:
```
NAME                  STATUS    PORTS
marry-me-kafka        running   0.0.0.0:9092->9092/tcp
marry-me-kafka-ui     running   0.0.0.0:8080->8080/tcp
marry-me-zookeeper    running   0.0.0.0:2181->2181/tcp
```

### Verify Kafka is Working

```bash
# Check Kafka is accepting connections
docker exec marry-me-kafka kafka-topics --bootstrap-server localhost:9092 --list
```

Or open the Kafka UI in your browser:
```
http://localhost:8080
```

### Stop Kafka

```bash
# Stop containers (keeps data)
docker-compose stop

# Stop and remove containers (keeps data volumes)
docker-compose down

# Stop and remove everything including data
docker-compose down -v
```

---

## End-to-End Walkthrough

### Quick Verify (No Kafka Required)

The fastest way to confirm everything works. Copy-paste ready:

```bash
# 1. Clone and enter project
git clone https://github.com/QwasarSV/eng_labs_marry_me.git
cd eng_labs_marry_me

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the test suite (should see all tests pass)
pytest

# 5. Run a 30-second demo (no Kafka needed)
python demo.py --duration 30
```

### Full Simulation (Requires Kafka)

Once you've verified the basics above, start Kafka and run the real simulation:

```bash
# 1. Start Kafka (wait ~30 seconds for full startup)
docker-compose up -d
sleep 30

# 2. Verify Kafka is running
docker-compose ps

# 3. Run the simulation
python simulation.py
```

### What Happens When You Run

```
┌─ STARTUP ──────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. Kafka topics are created automatically                                  │
│  2. Coordinator processes start (validate events)                          │
│  3. Organizer process starts (route events)                                │
│  4. Team processes start (handle events)                                   │
│     - Security (3 workers)                                                 │
│     - Clean Up (3 workers)                                                 │
│     - Catering (3 workers)                                                 │
│     - Officiant (3 workers)                                                │
│     - Waiters (3 workers)                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ SIMULATION (6 minutes) ───────────────────────────────────────────────────┐
│                                                                             │
│  Every ~2 seconds:                                                         │
│    1. Random event generated (brawl, dirty_table, music, etc.)            │
│    2. Event sent to Kafka topic "wedding-events"                          │
│    3. Coordinator validates → sends to "validated-events"                 │
│    4. Organizer routes → sends to "team-{name}" topic                     │
│    5. Team consumes → assigns to idle worker (if in idle phase)           │
│    6. Worker handles event (3 seconds)                                     │
│    7. If deadline missed → event expires → stress++                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─ RESULTS ──────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ============================================================              │
│  WEDDING SIMULATION COMPLETE                                               │
│  ============================================================              │
│    total_events: 180                                                       │
│    handled_events: 165                                                     │
│    expired_events: 15                                                      │
│    stress_level: 15                                                        │
│    success_rate: 91.7%                                                     │
│  ============================================================              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Monitor in Real-Time

While simulation runs, open another terminal:

```bash
# Watch Kafka UI (see messages flowing through topics)
open http://localhost:8080

# View simulation logs
tail -f logs/simulation_*.log

# Watch event log (JSON lines)
tail -f logs/events_*.jsonl
```

### Quick Test (30 seconds)

For a quick test without waiting 6 minutes (see also the [Quick Verify](#quick-verify-no-kafka-required) walkthrough above):

```bash
# Run demo mode (no Kafka needed, instant feedback)
python demo.py --duration 30

# Or with Kafka, use high speed + high event rate
python simulation.py --event-rate 2.0
```

### Cleanup After Running

```bash
# Stop Kafka containers
docker-compose down

# Remove log files
rm -rf logs/

# Deactivate virtual environment
deactivate
```

---

## Demo Mode (No Kafka Required)

The demo provides an interactive terminal-based visualization of the system without requiring Kafka. Perfect for demonstrations and as a foundation for building a UI.

### Quick Demo

```bash
python demo.py
```

### Demo Options

```bash
# Short 30-second demo
python demo.py --duration 30

# More workers for better performance
python demo.py --workers 5

# Faster simulation (2x speed)
python demo.py --speed 2

# Higher event rate (stress test)
python demo.py --rate 1.5

# Combined example
python demo.py --duration 60 --workers 4 --speed 1.5 --rate 1.0
```

### Demo Display

The demo shows real-time:
- **Wedding time** and simulation progress
- **Statistics**: total, handled, expired events and stress level
- **Priority breakdown**: events by HIGH/MEDIUM/LOW
- **Team status**: phase (READY/BUSY), workers, queue size, performance
- **Activity log**: recent events and actions
- **Final report**: analysis and recommendations

```
======================================================================
           MARRY ME - Wedding Event Management Demo
======================================================================

  Wedding Time: 01:30  |  Real Time: 45s / 60s  [=================     ]

  Statistics:
    Total Events:   42  |  Handled:   35  |  Expired:    3  |  Pending:    4
    Success Rate: 83.3%   [Stress: MEDIUM]

  Team Status:
  ------------------------------------------------------------------
  Security   READY | Workers: 1/3 working  | Queue:   2 | Done:   8 | Expired:   0
  Clean Up   BUSY  | Workers: 0/3 working  | Queue:   1 | Done:  12 | Expired:   1
  ...
```

---

## Running the Full Application (With Kafka)

> **Prerequisite**: Kafka must be running. See [Apache Kafka Setup](#apache-kafka-setup-docker) above.

### Quick Start (Random Events)

```bash
# Make sure Kafka is running first!
docker-compose ps  # Should show 3 containers running

# Run simulation
python simulation.py
```

This runs a 6-minute simulation generating random events at ~0.5 events/second.

### With Custom Parameters

```bash
# More workers and higher event rate
python simulation.py --workers 5 --event-rate 1.0

# Multiple coordinators (for load distribution)
python simulation.py --coordinators 3 --workers 4

# Stress test (lots of events)
python simulation.py --workers 2 --event-rate 2.0
```

### Using Predefined Events (Datasets)

Five datasets of 1000 events each are included (sourced from the [QwasarSV reference repo](https://github.com/QwasarSV/eng_labs_marry_me)). The loader automatically normalizes the external format (capitalized priorities, typos, etc.) to the internal format.

```bash
# Use one of the included datasets
python simulation.py --events-file dataset_1.json
python simulation.py --events-file dataset_3.json

# Generate a new dataset
python generate_datasets.py -o my_dataset.json -n 500
```

You can also create a custom event file. Both the internal format and the QwasarSV format are accepted:
```json
[
  {
    "id": 1,
    "event_type": "brawl",
    "priority": "High",
    "description": "Fight at the open bar",
    "timestamp": "01:30"
  },
  {
    "id": 2,
    "event_type": "bride",
    "priority": "High",
    "description": "Bride needs dress adjustment",
    "timestamp": "02:00"
  }
]
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--coordinators` | 2 | Number of coordinator processes |
| `--workers` | 3 | Workers per team |
| `--events-file` | None | JSON file with predefined events |
| `--event-rate` | 0.5 | Events per second (random mode) |

### Process Architecture

When you run `simulation.py`, it spawns multiple processes:

```
simulation.py (main process)
    │
    ├── Coordinator-0 (process) ─── validates events
    ├── Coordinator-1 (process) ─── validates events
    │
    ├── Organizer (process) ─────── routes events to teams
    │
    ├── Team-Security (process)
    │       ├── Worker-0 (thread)
    │       ├── Worker-1 (thread)
    │       └── Worker-2 (thread)
    │
    ├── Team-CleanUp (process)
    │       └── ... workers
    │
    ├── Team-Catering (process)
    │       └── ... workers
    │
    ├── Team-Officiant (process)
    │       └── ... workers
    │
    └── Team-Waiters (process)
            └── ... workers

Total: 1 main + 2 coordinators + 1 organizer + 5 teams = 9 processes
```

### Stopping the Simulation

Press `Ctrl+C` to stop gracefully. The simulation will:
1. Stop generating new events
2. Allow current events to complete (20 second drain period)
3. Terminate all worker processes
4. Print final statistics

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `NoBrokersAvailable` | Kafka not running | Run `docker-compose up -d` |
| `Connection refused :9092` | Kafka still starting | Wait 30 seconds, try again |
| No events processed | Organizer not routing | Check Kafka UI for messages |
| All events expiring | Workers too slow | Increase `--workers` |

---

## Testing

### Run All Tests

```bash
pytest
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Tests with Coverage Report

```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser to view report
```

### Run Specific Test Files

```bash
# Test only models
pytest tests/test_models.py

# Test only coordinator
pytest tests/test_coordinator.py

# Test configuration
pytest tests/test_config.py
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_models.py::TestEvent

# Run a specific test function
pytest tests/test_models.py::TestEvent::test_event_creation_basic
```

### Run Tests by Marker

```bash
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration
```

### Test Summary

| Module | Test File | Coverage |
|--------|-----------|----------|
| `config.py` | `tests/test_config.py` | Enums, mappings, constants |
| `models.py` | `tests/test_models.py` | Event, Worker, Team, Stats |
| `coordinator.py` | `tests/test_coordinator.py` | Validation, routing |
| `organizer.py` | `tests/test_organizer.py` | Event distribution |
| `team.py` | `tests/test_team.py` | Priority queue, routines |
| `simulation.py` | `tests/test_simulation.py` | Time conversion, stats |
| `logger.py` | `tests/test_logger.py` | Logging, reporting |

---

## Configuration

All configuration is centralized in `config.py`:

### Priority Timeframes

```python
Priority.HIGH   = 5 seconds   # Must handle within 5s
Priority.MEDIUM = 10 seconds  # Must handle within 10s
Priority.LOW    = 15 seconds  # Must handle within 15s
```

### Team Routines

| Team | Routine | Working | Idle | Description |
|------|---------|---------|------|-------------|
| Security | Standard | 20s | 5s | Regular work cycles |
| Clean Up | Intermittent | 5s | 5s | Frequent short breaks |
| Catering | Concentrated | 60s | 60s | Long work, long break |
| Officiant | Concentrated | 60s | 60s | Long work, long break |
| Waiters | Standard | 20s | 5s | Regular work cycles |

### Kafka Configuration

```python
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
```

---

## Project Structure

```
englab4/
├── .gitignore             # Git ignore rules
├── demo.py                # Interactive demo (no Kafka required)
├── simulation.py          # Full simulation with Kafka
├── config.py              # Configuration constants and enums
├── models.py              # Data models (Event, Worker, Team, Stats)
├── coordinator.py         # Event validation and forwarding
├── organizer.py           # Event routing to teams
├── team.py                # Team management and worker dispatch
├── logger.py              # Event logging and monitoring
├── requirements.txt       # Python dependencies
├── pytest.ini             # Pytest configuration
├── docker-compose.yml     # Kafka infrastructure
├── dataset_1.json         # 1000-event dataset (from QwasarSV reference repo)
├── dataset_2.json         # 1000-event dataset
├── dataset_3.json         # 1000-event dataset
├── dataset_4.json         # 1000-event dataset
├── dataset_5.json         # 1000-event dataset
├── generate_datasets.py   # Dataset generator script
├── README.md              # This file
├── logs/                  # Generated log files (created at runtime)
│   ├── events_*.jsonl     # Event log (JSON Lines format)
│   ├── stats_*.json       # Final statistics
│   └── simulation_*.log   # Full simulation log
└── tests/                 # Test suite
    ├── __init__.py
    ├── conftest.py        # Shared fixtures
    ├── test_config.py     # Config tests
    ├── test_models.py     # Model tests
    ├── test_coordinator.py # Coordinator tests
    ├── test_organizer.py  # Organizer tests
    ├── test_team.py       # Team tests
    ├── test_simulation.py # Simulation tests
    └── test_logger.py     # Logger tests
```

---

## Event Types

### Security Team
| Event Type | Description |
|------------|-------------|
| `brawl` | Physical altercation between guests |
| `not_on_list` | Unauthorized person attempting entry |
| `accident` | Safety incident requiring security |

### Clean Up Team
| Event Type | Description |
|------------|-------------|
| `dirty_table` | Table needs cleaning |
| `broken_items` | Broken glass/items need cleanup |
| `dirty_floor` | Floor spill or mess |

### Catering Team
| Event Type | Description |
|------------|-------------|
| `bad_food` | Food quality complaint |
| `music` | Music-related issues |
| `feeling_ill` | Guest feeling unwell (food-related) |

### Officiant Team
| Event Type | Description |
|------------|-------------|
| `bride` | Bride needs assistance |
| `groom` | Groom needs assistance |

### Waiters Team
| Event Type | Description |
|------------|-------------|
| `broken_items` | Broken items at tables |
| `accident` | Minor accidents at tables |
| `bad_food` | Food service issues |

> **Note**: Some event types (broken_items, accident, bad_food) can be handled by multiple teams.

---

## Timing Rules

### Simulation Time Scale

- **1 simulation second = 1 wedding minute**
- **Total simulation: 6 minutes = 6 hours wedding time**
- Wedding time runs from 00:00 to 06:00

### Event Handling

- Each event takes **3 seconds** to handle, regardless of type or priority
- Workers follow their team's routine cycle (working/idle phases)
- During **working phase**: Workers are unavailable
- During **idle phase**: Workers can pick up events

### Stress Calculation

- Each expired (unhandled) event adds **+1 stress level**
- Goal: Minimize stress level by handling events before deadlines

---

## Monitoring and Logging

### Log Files

Logs are written to the `logs/` directory:

| File Pattern | Format | Content |
|--------------|--------|---------|
| `events_*.jsonl` | JSON Lines | Individual event records |
| `stats_*.json` | JSON | Final simulation statistics |
| `simulation_*.log` | Text | Full application log |

### Kafka UI

Access the Kafka UI at http://localhost:8080 to:
- View topics and messages
- Monitor consumer groups
- Inspect message contents

### Final Statistics

At the end of each simulation, you'll see:

```
============================================================
WEDDING SIMULATION COMPLETE
============================================================
  total_events: 180
  handled_events: 165
  expired_events: 15
  stress_level: 15
  success_rate: 91.7%
============================================================
```

---

## Troubleshooting

### Kafka Connection Issues

```bash
# Check if Kafka is running
docker-compose ps

# View Kafka logs
docker-compose logs kafka

# Restart Kafka
docker-compose restart kafka
```

### Port Already in Use

```bash
# Find process using port 9092
lsof -i :9092

# Kill the process or change ports in docker-compose.yml
```

### Python Import Errors

```bash
# Make sure you're in the project directory
cd /path/to/eng_labs_marry_me

# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Tests Failing

```bash
# Run tests with more verbose output
pytest -vvs

# Run a single failing test for debugging
pytest tests/test_models.py::TestEvent::test_event_creation_basic -vvs
```

### Clean Up

```bash
# Stop Kafka
docker-compose down

# Remove Kafka data volumes
docker-compose down -v

# Remove log files
rm -rf logs/
```

---

## License

This project is part of the Qwasar Master's of Science in Computer Science program.
Private and confidential. Do not distribute.
