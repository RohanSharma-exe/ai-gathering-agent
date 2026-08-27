"""Capture and inspect live desktop frames without sending game input.

This is the calibration bridge between the tested perception code and a real
Albion window. It intentionally performs no mouse/keyboard actions.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from desktop import Desktop
from observation import UIObservation
from runtime import ObservationRuntime, RuntimeConfig


def observe_frame(image: object) -> UIObservation:
    """Return the current conservative observation for one screenshot."""
    # Perception is intentionally conservative until the Albion UI is calibrated.
    # Keeping this function separate lets us replace it with the real detector
    # without changing the runtime or desktop boundary.
    if not hasattr(image, "size"):
        raise TypeError("expected a screenshot image")
    return UIObservation()


def describe(frame: object) -> None:
    observation = getattr(frame, "observation", None)
    image = getattr(frame, "image", None)
    size = getattr(image, "size", None)
    print(f"frame={getattr(frame, 'index', '?')} size={size} observation={observation}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe the desktop without controlling it")
    parser.add_argument("--frames", type=int, default=5, help="number of screenshots to capture")
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between screenshots")
    parser.add_argument("--output", type=Path, default=Path("screenshots/live"))
    args = parser.parse_args()

    runtime = ObservationRuntime(
        Desktop(dry_run=True),
        observe_frame,
        RuntimeConfig(
            interval_seconds=args.interval,
            max_frames=args.frames,
            save_frames=True,
            output_dir=args.output,
        ),
    )
    print("Observation-only mode: no mouse or keyboard input will be sent.")
    print(f"Saving frames to: {args.output.resolve()}")
    runtime.run(describe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
