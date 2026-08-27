# Minimal Visual Gathering Agent

A small local-first prototype for experimenting with a visual gathering-agent brain. The V1 system accepts a high-level gathering objective, converts observations into typed state, chooses a deterministic next decision, proposes an action, and verifies whether the action boundary accepted it.

## V1 objectives

- `Gather leather`
- `Gather fiber`
- `Gather ore`
- `Gather wood`
- `Gather stone`
- `Gather everything`

The brain models target selection, exploration, inventory return thresholds, safe-area constraints, combat-before-gathering for animal targets, and recovery states.

## Architecture

```text
objective
   ↓
state ← observation
   ↓
planner
   ↓
decision
   ↓
action boundary
   ↓
verification
```

Routine decisions are local and deterministic. There is no required external API, LLM, database, or agent framework.

## Setup

Requires Python 3.13+ and `uv`.

```cmd
uv sync
uv run pytest -q
```

## Scope boundary

The action executor in V1 is a controlled/no-op boundary. This project does not contain autonomous live-game control code.
