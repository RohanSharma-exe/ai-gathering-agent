"""Guarded live runner for the Albion gathering prototype."""

from __future__ import annotations

import argparse
from typing import Callable

from actions import Action, ActionExecutor, PyAutoGUIExecutor
from albion_perception import AlbionUIObserver
from desktop import Desktop
from live_control import LiveControlConfig, LiveControlRuntime
from live_observe import activate_albion_window, albion_client_rect, crop_albion_client
from observation import UIObservation
from state import Objective, Target
from vision import Observation


class AlbionScreenshotSource:
    """Screenshot adapter that captures the desktop only in memory."""

    def __init__(self, desktop: Desktop) -> None:
        self.desktop = desktop

    def screenshot(self):
        return self.desktop.screenshot()


def _desktop_targets(targets: tuple[Target, ...], image: object) -> tuple[Target, ...]:
    rect = albion_client_rect()
    if rect is None:
        return targets
    left, top, right, bottom = rect
    screen_width, screen_height = image.size
    client_width = right - left
    client_height = bottom - top
    if client_width <= 0 or client_height <= 0:
        return ()
    mapped: list[Target] = []
    for target in targets:
        if target.screen_x is None or target.screen_y is None:
            mapped.append(target)
            continue
        screen_x = (left + target.screen_x * client_width) / screen_width
        screen_y = (top + target.screen_y * client_height) / screen_height
        mapped.append(Target(target.kind, target.resource, target.distance, max(0.0, min(1.0, screen_x)), max(0.0, min(1.0, screen_y))))
    return tuple(mapped)


def observe_factory(resource: str = "wood") -> tuple[AlbionUIObserver, Callable[[object], Observation]]:
    observer = AlbionUIObserver()
    wanted = {resource.strip().lower()}

    def observe(image: object) -> Observation:
        client_image = crop_albion_client(image)
        ui: UIObservation = observer.observe(client_image, resources=wanted)
        confidence = 1.0 if ui.mounted is not None else 0.0
        return Observation(
            inventory_percent=0.0 if ui.inventory_percent is None else ui.inventory_percent,
            mounted=False if ui.mounted is None else ui.mounted,
            targets=_desktop_targets(ui.targets, image),
            player_confidence=confidence,
            mounted_confidence=confidence,
        )

    return observer, observe


def _print_dry_run_action(action: Action) -> None:
    details = [f"action={action.kind.value}"]
    if action.target_id is not None:
        details.append(f"target={action.target_id}")
    if action.x is not None and action.y is not None:
        details.append(f"x={action.x} y={action.y}")
    if action.key is not None:
        details.append(f"key={action.key}")
    print(" ".join(details))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the guarded Albion gathering controller")
    parser.add_argument("--resource", default="wood", help="resource to gather")
    parser.add_argument("--frames", type=int, default=5, help="maximum observation frames")
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between frames")
    parser.add_argument("--dismount-key", default="a", help="key used to mount/dismount")
    parser.add_argument("--max-gathers", type=int, default=None, help="stop after this many gather actions")
    parser.add_argument("--dismount-only", action="store_true", help="test dismounting only; never gather")
    parser.add_argument("--live", action="store_true", help="ENABLE real mouse/keyboard input")
    args = parser.parse_args()

    if args.frames < 1:
        parser.error("--frames must be positive")
    if args.interval < 0:
        parser.error("--interval cannot be negative")
    if args.max_gathers is not None and args.max_gathers < 1:
        parser.error("--max-gathers must be positive")
    if args.dismount_only and args.max_gathers is not None:
        parser.error("--dismount-only cannot be combined with --max-gathers")

    desktop = Desktop(dry_run=True)
    source = AlbionScreenshotSource(desktop)
    _, observe = observe_factory(args.resource)
    executor: ActionExecutor = PyAutoGUIExecutor(dry_run=not args.live)
    config = LiveControlConfig(
        max_frames=args.frames,
        dry_run=not args.live,
        dismount_key=args.dismount_key,
        gather_cooldown=args.interval,
        max_gathers=args.max_gathers,
        dismount_only=args.dismount_only,
    )

    print("=== Albion Gathering Agent ===")
    print(f"mode={'LIVE INPUT ENABLED' if args.live else 'DRY-RUN (no input)'}")
    print(f"resource={args.resource} frames={args.frames} interval={args.interval}s")
    print("screenshots=memory-only")
    if args.max_gathers is not None:
        print(f"max_gathers={args.max_gathers}")
    if args.dismount_only:
        print("dismount_only=true")
    if args.live:
        if not activate_albion_window():
            print("ERROR: could not activate 'Albion Online Client'; no input sent.")
            return 2
        print("Albion window activated; real input is enabled.")

    runtime = LiveControlRuntime(source, observe, executor, Objective(args.resource), config)
    original_execute = runtime._execute

    def diagnostic_execute(action: Action) -> bool:
        if config.dry_run:
            _print_dry_run_action(action)
        return original_execute(action)

    runtime._execute = diagnostic_execute
    processed = runtime.run()
    print(f"stopped after {processed} frame(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
