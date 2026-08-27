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

## Controlled live-game test

The repository now contains a guarded live-control loop in `live_control.py`.

Dry-run first:

```cmd
uv run python live_control.py --objective fiber --frames 1
```

For the first real input test, keep Albion Online focused and run:

```cmd
uv run python live_control.py --objective fiber --frames 1 --dismount-key a --live
```

`A` is the commonly reported PC mount/dismount binding, but the command accepts a different key if your bindings are customized. The live flag is required before any real keyboard or mouse input is sent.

The current Albion perception backend reliably reports mounted/unmounted UI state, but it does not yet identify resource nodes from pixels. A manual target can therefore be supplied for a controlled click test using normalized screen coordinates:

```cmd
uv run python live_control.py --objective fiber --frames 2 --dismount-key a --target-x 0.52 --target-y 0.48 --live
```

The controller stops rather than guessing when it cannot produce a safe target coordinate, reaches a return/explore decision, or an input action is rejected.

## Scope boundary

The action executor is now capable of controlled real primitive input (click, movement, key press, and target interaction) through PyAutoGUI, but autonomous resource-node detection is still a separate perception task. The first live milestone is therefore **observe mounted state → dismount → controlled target click**, followed by replacing the manual target with a real local resource detector.
