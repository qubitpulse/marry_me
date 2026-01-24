# Marry Me - Wedding Event Management System

An event-driven application that manages wedding events using Apache Kafka and Python multiprocessing.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Event Source   │────▶│   Coordinator   │────▶│  Kafka Broker   │
│   (Producer)    │     │   (Validator)   │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        ▼                ▼               ▼               ▼                ▼
                 ┌───────────┐    ┌───────────┐   ┌───────────┐   ┌───────────┐    ┌───────────┐
                 │ Security  │    │ Clean_up  │   │ Catering  │   │ Officiant │    │  Waiters  │
                 │  (Topic)  │    │  (Topic)  │   │  (Topic)  │   │  (Topic)  │    │  (Topic)  │
                 └─────┬─────┘    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘    └─────┬─────┘
                       │                │               │               │                │
                   Workers          Workers         Workers         Workers          Workers
                 (Processes)      (Processes)     (Processes)     (Processes)      (Processes)
```

## Components

- **Coordinator**: Receives and validates events, forwards to Kafka
- **Organizer**: Routes validated events to appropriate team topics
- **Teams**: Security, Clean_up, Catering, Officiant, Waiters
- **Workers**: Handle individual events within their team

## Prerequisites

- Docker and Docker Compose
- Python 3.10+

## Setup

1. **Start Kafka:**
   ```bash
   docker-compose up -d
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Kafka is running:**
   - Kafka UI available at: http://localhost:8080

## Running the Simulation

### Random event generation:
```bash
python simulation.py --workers 3 --event-rate 0.5
```

### With predefined events:
```bash
python simulation.py --events-file sample_events.json
```

### Options:
- `--coordinators`: Number of coordinator processes (default: 2)
- `--workers`: Workers per team (default: 3)
- `--events-file`: JSON file with predefined events
- `--event-rate`: Events per second for random mode (default: 0.5)

## Timing Rules

### Priority Timeframes (before event expires):
- HIGH: 5 seconds
- MEDIUM: 10 seconds
- LOW: 15 seconds

### Team Routines (working/idle cycles):
| Team      | Routine       | Working | Idle |
|-----------|---------------|---------|------|
| Security  | Standard      | 20s     | 5s   |
| Clean_up  | Intermittent  | 5s      | 5s   |
| Catering  | Concentrated  | 60s     | 60s  |
| Officiant | Concentrated  | 60s     | 60s  |
| Waiters   | Standard      | 20s     | 5s   |

## Event Types by Team

- **Security**: brawl, not_on_list, accident
- **Clean_up**: dirty_table, broken_items, dirty_floor
- **Catering**: bad_food, music, feeling_ill
- **Officiant**: bride, groom
- **Waiters**: broken_items, accident, bad_food

## Logs

Logs are written to the `logs/` directory:
- `simulation_*.log`: Full simulation log
- `events_*.jsonl`: Event records in JSON Lines format
- `stats_*.json`: Final statistics

## Stress Level

The stress level increases each time an event expires without being handled. The goal is to minimize the stress level by efficiently routing events to available workers.

## Stopping

Press `Ctrl+C` to stop the simulation gracefully.

To stop Kafka:
```bash
docker-compose down
```

## Project Structure

```
.
├── config.py           # Configuration constants
├── models.py           # Data models (Event, Worker, Team)
├── coordinator.py      # Event validation and forwarding
├── organizer.py        # Event routing to teams
├── team.py             # Team management and worker dispatch
├── simulation.py       # Main simulation orchestrator
├── logger.py           # Logging and monitoring
├── sample_events.json  # Sample event data
├── docker-compose.yml  # Kafka infrastructure
├── requirements.txt    # Python dependencies
└── README.md           # This file
```
