"""Guarded live runner for the Albion gathering prototype.

The runner is deliberately conservative:
- dry-run is the default;
- --live is required before any desktop input can be sent;
- the first live invocation should use a small --frames value;
- screenshots are never persisted by this runner;
- LiveControlRuntime remains the single decision/action boundary.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from actions import ActionExecutor, PyAutoGUIExecutor
from albion_perception import AlbionUIObserver
from desktop import Desktop
from live_control import LiveControlConfig, LiveControlRuntime
from observation import UIObservation
from state import Objective


class AlbionScreenshotSource:
    """Screenshot adapter that captures the desktop only in memory."""

    def __init__(self, desktop: Desktop) -> None:
        self.desktop = desktop

    def screenshot(self):
        return self.desktop.screenshot()


def observe_factory() -> tuple[AlbionUIObserver, callable]:
    observer = AlbionUIObserver()

    def observe(image: object) -> UIObservation:
        return observer.observe(image)

    return observer, observe


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the guarded Albion gathering controller")
    parser.add_argument("--resource", default="wood", help="resource to gather")
    parser.add_argument("--frames", type=int, default=5, help="maximum observation frames")
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between frames")
    parser.add_argument("--dismount-key", default="a", help="key used to mount/dismount")
    parser.add_argument("--live", action="store_true", help="ENABLE real mouse/keyboard input")
    args = parser.parse_args()

    if args.frames < 1:
        parser.error("--frames must be positive")
    if args.interval < 0:
        parser.error("--interval cannot be negative")

    # Desktop screenshots are always taken without desktop input here.
    desktop = Desktop(dry_run=True)
    source = AlbionScreenshotSource(desktop)
    _, observe = observe_factory()

    executor: ActionExecutor = PyAutoGUIExecutor(dry_run=not args.live)
    config = LiveControlConfig(
        max_frames=args.frames,
        dry_run=not args.live,
        dismount_key=args.dismount_key,
        gather_cooldown=args.interval,
    )

    print("=== Albion Gathering Agent ===")
    print(f"mode={'LIVE INPUT ENABLED' if args.live else 'DRY-RUN (no input)'}")
    print(f"resource={args.resource} frames={args.frames} interval={args.interval}s")
    print("screenshots=memory-only")
    if args.live:
        print("WARNING: real mouse/keyboard input is enabled.")
        print("Keep Albion focused and use PyAutoGUI's emergency stop if needed.")

    runtime = LiveControlRuntime(
        source=source,
        observe=observe,
        executor=executor,
        objective=Objective(args.resource),
        config=config,
    )
    processed = runtime.run()
    print(f"stopped after {processed} frame(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
