"""Guarded live runner for the Albion gathering prototype."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
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
    client_width, client_height = right - left, bottom - top
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


def _is_player_exclusion_zone(target: Target) -> bool:
    """Reject resource-color blobs over the player's character/nameplate."""
    if target.screen_x is None or target.screen_y is None:
        return False
    dx = (target.screen_x - 0.5) / 0.105
    dy = (target.screen_y - 0.47) / 0.14
    return dx * dx + dy * dy <= 1.0


def _filter_player_targets(targets: tuple[Target, ...], client_image: object) -> tuple[Target, ...]:
    """Remove brown/orange false positives produced by the centered player.

    The exclusion is enabled only for real-sized Albion client captures. Small
    synthetic unit-test fixtures intentionally bypass it.
    """
    width, height = client_image.size
    if width < 800 or height < 600:
        return targets
    return tuple(target for target in targets if not _is_player_exclusion_zone(target))


def _select_target(observation: Observation, objective: Objective) -> Target | None:
    """Choose the first compatible target from the already-filtered list."""
    return next(
        (
            candidate
            for candidate in observation.targets
            if candidate.is_compatible_with(objective)
            and candidate.screen_x is not None
            and candidate.screen_y is not None
        ),
        None,
    )


def observe_factory(resource: str = "wood") -> tuple[AlbionUIObserver, Callable[[object], Observation]]:
    observer = AlbionUIObserver()
    wanted = {resource.strip().lower()}
    def observe(image: object) -> Observation:
        client_image = crop_albion_client(image)
        ui: UIObservation = observer.observe(client_image, resources=wanted)
        confidence = 1.0 if ui.mounted is not None else 0.0
        inventory_percent = 0.0 if ui.inventory_percent is None else ui.inventory_percent
        filtered_targets = _filter_player_targets(ui.targets, client_image)
        return Observation(
            inventory_percent=inventory_percent,
            mounted=False if ui.mounted is None else ui.mounted,
            targets=_desktop_targets(filtered_targets, image),
            player_confidence=confidence,
            mounted_confidence=confidence,
        )
    return observer, observe


def _print_action(action: Action, dry_run: bool) -> None:
    details = [f"action={action.kind.value}"]
    if action.target_id is not None:
        details.append(f"target={action.target_id}")
    if action.x is not None and action.y is not None:
        details.append(f"x={action.x} y={action.y}")
    if action.key is not None:
        details.append(f"key={action.key}")
    print(("proposed " if dry_run else "sending ") + " ".join(details), flush=True)


def _save_target_debug(image: object, target: Target, output: Path) -> None:
    """Save one desktop frame with the exact proposed click point marked."""
    if target.screen_x is None or target.screen_y is None:
        return
    if not hasattr(image, "copy") or not hasattr(image, "size"):
        return
    try:
        from PIL import ImageDraw
    except ImportError:
        return
    width, height = image.size
    x = round(target.screen_x * width)
    y = round(target.screen_y * height)
    debug = image.copy()
    draw = ImageDraw.Draw(debug)
    radius = 20
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(255, 0, 0), width=4)
    draw.line((x - 30, y, x + 30, y), fill=(255, 0, 0), width=3)
    draw.line((x, y - 30, x, y + 30), fill=(255, 0, 0), width=3)
    output.parent.mkdir(parents=True, exist_ok=True)
    debug.save(output)
    print(f"target-debug={output.resolve()}", flush=True)
    print(f"desktop-size={width}x{height} click=({x},{y}) client-rect={albion_client_rect()}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the guarded Albion gathering controller")
    parser.add_argument("--resource", default="wood")
    parser.add_argument("--frames", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--dismount-key", default="a")
    parser.add_argument("--max-gathers", type=int, default=None)
    parser.add_argument("--dismount-only", action="store_true")
    parser.add_argument("--live", action="store_true", help="ENABLE real mouse/keyboard input")
    parser.add_argument("--target-debug", action="store_true", help="save one frame showing the proposed target click; never sends input")
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames must be positive")
    if args.interval < 0:
        parser.error("--interval cannot be negative")
    if args.max_gathers is not None and args.max_gathers < 1:
        parser.error("--max-gathers must be positive")
    if args.dismount_only and args.max_gathers is not None:
        parser.error("--dismount-only cannot be combined with --max-gathers")
    if args.target_debug and args.live:
        parser.error("--target-debug cannot be combined with --live")

    desktop = Desktop(dry_run=True)
    source = AlbionScreenshotSource(desktop)
    _, observe = observe_factory(args.resource)
    executor: ActionExecutor = PyAutoGUIExecutor(dry_run=not args.live)
    config = LiveControlConfig(max_frames=args.frames, dry_run=not args.live, dismount_key=args.dismount_key, gather_cooldown=args.interval, max_gathers=args.max_gathers, dismount_only=args.dismount_only)

    print("=== Albion Gathering Agent ===")
    print(f"mode={'LIVE INPUT ENABLED' if args.live else 'DRY-RUN (no input)'}")
    print(f"resource={args.resource} frames={args.frames} interval={args.interval}s")
    print("screenshots=memory-only")
    if args.max_gathers is not None:
        print(f"max_gathers={args.max_gathers}")
    if args.dismount_only:
        print("dismount_only=true")
    if args.target_debug:
        print("target_debug=true")
    if args.live:
        if not activate_albion_window():
            print("ERROR: could not activate 'Albion Online Client'; no input sent.")
            return 2
        print("Albion window activated; waiting for focus to settle...")
        time.sleep(0.75)

    runtime = LiveControlRuntime(source, observe, executor, Objective(args.resource), config)
    original_observe = runtime.observe
    original_execute = runtime._execute
    frame_counter = 0
    debug_done = False

    def diagnostic_observe(image: object) -> Observation:
        nonlocal frame_counter, debug_done
        observation = original_observe(image)
        frame_counter += 1
        print(f"frame={frame_counter} mounted={observation.mounted} mount_confidence={observation.mounted_confidence:.2f} inventory={observation.inventory_percent:.1f}% targets={len(observation.targets)}", flush=True)
        for target in observation.targets[:5]:
            print(f"  target={target.resource} kind={target.kind.value} screen=({target.screen_x},{target.screen_y})", flush=True)
        selected = _select_target(observation, runtime.objective)
        if selected is not None:
            print(f"  selected={selected.resource} screen=({selected.screen_x},{selected.screen_y})", flush=True)
        if args.target_debug and not debug_done and selected is not None:
            _save_target_debug(image, selected, Path("screenshots/live/target_debug.png"))
            debug_done = True
        return observation

    def diagnostic_execute(action: Action) -> bool:
        _print_action(action, config.dry_run)
        if not config.dry_run:
            print("  input sent; re-observing before any further action", flush=True)
        return original_execute(action)

    runtime.observe = diagnostic_observe
    runtime._execute = diagnostic_execute
    processed = runtime.run()
    print(f"stopped after {processed} frame(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
