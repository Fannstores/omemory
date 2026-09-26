# Owner Memory usage reference

## Lifecycle

```text
project/session starts
      ↓
search relevant memory
      ↓
verify against current evidence
      ↓
work
      ↓
extract durable outcome
      ↓
deduplicate + classify
      ↓
save with provenance/confidence
```

## Storage rule

`.omemory/` is portable and inspectable. JSON records are the canonical records. `indexes/` is reserved for derived search data and can be rebuilt or deleted without losing memory.

## Categories

- `knowledge`: durable project facts
- `experience`: what happened and what worked/failed
- `decision`: deliberate choices and reasons
- `workflow`: repeatable procedures
- `preference`: explicit working preferences
- `project-state`: current milestones/state that can become stale

## Safety

Never infer secrets from memory. Avoid storing credentials and tokens. Treat memories containing external claims as unverified until their provenance and current state are checked.
