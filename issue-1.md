# Issue #1: Architecture Refactoring Suggestions

Ranked by utility for this project, based on [qubitpulse/marry_me#1](https://github.com/qubitpulse/marry_me/issues/1).

| Rank | Suggestion | Why |
|------|-----------|-----|
| 1 | **ThreadPoolExecutor** instead of unbounded threads | Prevents crashing under load from the 1000-event datasets, small change |
| 2 | **threading.Event** instead of polling | Removes wasteful `sleep(0.1)` loop, cleaner and lower latency |
| 3 | **Input validation with pydantic** | Catches bad data early, especially useful now that we ingest external datasets |
| 4 | **Background thread for expired event cleanup** | Current O(n) scan under lock blocks event processing, gets worse with big datasets |
| 5 | **Rate limiting on coordinator** | Prevents overwhelming teams when injecting 1000 events from a dataset file |
| 6 | **Per-team stats queues** | Reduces contention on the single shared stats queue across 5 team processes |
| 7 | **Async Kafka consumer** | Nice-to-have but current blocking approach works fine at this scale |
| 8 | **Circuit breaker pattern** | Overkill for a local simulation, useful if this were a real production service |
| 9 | **Celery/Redis distributed workers** | Complete rewrite, only makes sense if you need multi-machine scaling |
| 10 | **PostgreSQL persistence** | Production concern, not a simulation concern |

## Summary

- **Items 1-6**: Practical improvements that help with the 1000-event datasets we now ingest from the QwasarSV reference repo.
- **Items 7-10**: Architectural upgrades that would turn this into a different project entirely.
