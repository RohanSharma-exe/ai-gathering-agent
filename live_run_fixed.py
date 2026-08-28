"""Temporary corrected guarded live runner using the Albion UI observer."""

from __future__ import annotations

import argparse
from typing import Callable

from actions import ActionExecutor, PyAutoGUIExecutor
from albion_perception import AlbionUIObserver
from desktop import Desktop
from live_control import LiveControlConfig, LiveControlRuntime
from state import Objective
from vision import Observation


class AlbionScreenshotSource:
    def __init__(self, desktop: Desktop) -> None:
        self.desktop = desktop

    def screenshot(self):
        return self.desktop.screenshot()


def observe_factory() -> Callable[[object], Observation]:
    observer = AlbionUIObserver()

    def observe(image: object) -> Observation:
        ui = observer.observe(image)
        confidence = 1.0 if ui.mounted is not None else 0.0
        return Observation(
            inventory_percent=0.0 if ui.inventory_percent is None else ui.inventory_percent,
            mounted=False if ui.mounted is None else ui.mounted,
            targets=(),
            player_confidence=confidence,
            mounted_confidence=confidence,
        )

    return observe


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the guarded Albion gathering controller")
    parser.add_argument("--resource", default="wood")
    parser.add_argument("--frames", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--dismount-key", default="a")
    parser.add_argument("--live", action="store_true", help="enable real mouse/keyboard input")
    args = parser.parse_args()

    if args.frames < 1:
        parser.error("--frames must be positive")
    if args.interval < 0:
        parser.error("--interval cannot be negative")

    desktop = Desktop(dry_run=True)
    runtime = LiveControlRuntime(
        source=AlbionScreenshotSource(desktop),
        observe=observe_factory(),
        executor=PyAutoGUIExecutor(dry_run=not args.live),
        objective=Objective(args.resource),
        config=LiveControlConfig(
            max_frames=args.frames,
            dry_run=not args.live,
            dismount_key=args.dismount_key,
            gather_cooldown=args.interval,
        ),
    )

    print("=== Albion Gathering Agent ===")
    print(f"mode={'LIVE INPUT ENABLED' if args.live else 'DRY-RUN (no input)'}")
    print(f"resource={args.resource} frames={args.frames} interval={args.interval}s")
    print("screenshots=memory-only")
    processed = runtime.run()
    print(f"stopped after {processed} frame(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
