# Marry Me - Wedding Event Management System

An event-driven application for managing wedding events using Apache Kafka and Python multiprocessing. Built as part of the Qwasar Master's of Science in Computer Science program.

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

### 1. Clone or Navigate to the Project

```bash
cd /path/to/englab4
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

### 4. Start Kafka Infrastructure

```bash
docker-compose up -d
```

This starts:
- **Zookeeper** on port 2181
- **Kafka** on port 9092
- **Kafka UI** on port 8080 (web interface)

### 5. Verify Kafka is Running

```bash
# Check containers are running
docker-compose ps

# View Kafka UI
open http://localhost:8080  # Or visit in browser
```

---

## Running the Application

### Quick Start (Random Events)

```bash
python simulation.py
```

This runs a 6-minute simulation generating random events at ~0.5 events/second.

### With Custom Parameters

```bash
# More workers and higher event rate
python simulation.py --workers 5 --event-rate 1.0

# Multiple coordinators
python simulation.py --coordinators 3 --workers 4
```

### Using Predefined Events

```bash
python simulation.py --events-file sample_events.json
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--coordinators` | 2 | Number of coordinator processes |
| `--workers` | 3 | Workers per team |
| `--events-file` | None | JSON file with predefined events |
| `--event-rate` | 0.5 | Events per second (random mode) |

### Stopping the Simulation

Press `Ctrl+C` to stop gracefully. The simulation will:
1. Stop generating new events
2. Allow current events to complete
3. Print final statistics

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
├── config.py              # Configuration constants and enums
├── models.py              # Data models (Event, Worker, Team, Stats)
├── coordinator.py         # Event validation and forwarding
├── organizer.py           # Event routing to teams
├── team.py                # Team management and worker dispatch
├── simulation.py          # Main simulation orchestrator
├── logger.py              # Event logging and monitoring
├── requirements.txt       # Python dependencies
├── pytest.ini             # Pytest configuration
├── docker-compose.yml     # Kafka infrastructure
├── sample_events.json     # Sample event data for testing
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
cd /path/to/englab4

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
