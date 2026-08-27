"""Controlled live-game loop for the Albion gathering-agent prototype.

The loop is intentionally conservative: real input requires ``--live`` and
stops when perception is uncertain, a target has no safe screen coordinates,
or the action boundary rejects an action.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from actions import Action, ActionExecutor, ActionKind, PyAutoGUIExecutor
from albion_perception import AlbionUIObserver
from desktop import Desktop
from live_observe import observe_frame
from main import action_for_decision, state_from_observation
from observation import UIObservation
from planner import DecisionKind, decide
from state import Objective, Target, TargetKind
from vision import Observation


@dataclass(frozen=True)
class LiveControlConfig:
    """Safety and pacing controls for the live loop."""

    interval_seconds: float = 0.25
    max_frames: int | None = 20
    dry_run: bool = True
    dismount_key: str | None = "a"
    target_x: float | None = None
    target_y: float | None = None
    min_perception_confidence: float = 0.9
    save_frames: bool = False
    output_dir: Path = Path("screenshots/live")

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if self.max_frames is not None and self.max_frames < 1:
            raise ValueError("max_frames must be positive when provided")
        if not 0 <= self.min_perception_confidence <= 1:
            raise ValueError("min_perception_confidence must be between 0 and 1")
        for name, value in (("target_x", self.target_x), ("target_y", self.target_y)):
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if (self.target_x is None) != (self.target_y is None):
            raise ValueError("target_x and target_y must be provided together")


class AlbionControlObserver:
    """Bridge Albion UI perception into the planner observation model.

    The current Albion perception backend knows mounted state but does not yet
    identify resource nodes. Optional normalized target coordinates provide a
    controlled manual target for the first end-to-end click test.
    """

    def __init__(
        self,
        objective: Objective,
        target_x: float | None = None,
        target_y: float | None = None,
        observer: AlbionUIObserver | None = None,
    ) -> None:
        self.objective = objective
        self.target_x = target_x
        self.target_y = target_y
        self.observer = observer

    def __call__(self, image: object) -> Observation:
        ui = self.observer.observe(image) if self.observer is not None else observe_frame(image)
        return self.to_observation(ui)

    def to_observation(self, ui: UIObservation) -> Observation:
        targets: tuple[Target, ...] = ()
        if (
            ui.mounted is False
            and self.target_x is not None
            and self.target_y is not None
            and self.objective.resource != "everything"
        ):
            targets = (
                Target(
                    kind=TargetKind.RESOURCE,
                    resource=self.objective.resource,
                    distance=0.0,
                    screen_x=self.target_x,
                    screen_y=self.target_y,
                ),
            )
        return Observation(
            inventory_percent=ui.inventory_percent or 0.0,
            mounted=bool(ui.mounted),
            mounted_confidence=1.0 if ui.mounted is not None else 0.0,
            targets=targets,
        )


class LiveControlRuntime:
    """Capture -> observe -> decide -> execute -> verify."""

    def __init__(
        self,
        source: object,
        observer: Callable[[object], Observation],
        executor: ActionExecutor,
        objective: Objective,
        config: LiveControlConfig | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self.observer = observer
        self.executor = executor
        self.objective = objective
        self.config = config or LiveControlConfig()
        self.sleep = sleep

    def _capture(self, index: int) -> object:
        path: Path | None = None
        if self.config.save_frames:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.config.output_dir / f"control_{index:06d}.png"
        return self.source.screenshot(path)

    def _action_for_observation(self, observation: Observation, image: object) -> Action | None:
        if observation.mounted_confidence < self.config.min_perception_confidence:
            return None

        if observation.mounted:
            if not self.config.dismount_key:
                return None
            return Action(ActionKind.PRESS_KEY, key=self.config.dismount_key)

        state = state_from_observation(self.objective, observation)
        decision = decide(state)
        if decision.kind in {DecisionKind.RETURN, DecisionKind.EXPLORE}:
            return None

        action = action_for_decision(decision, screen_size=getattr(image, "size", (1920, 1080)))
        if action.kind in {
            ActionKind.WAIT,
            ActionKind.CHANGE_AREA,
            ActionKind.RETURN_TO_STORAGE,
        }:
            return None
        if action.kind in {ActionKind.GATHER, ActionKind.INTERACT, ActionKind.ATTACK}:
            if action.x is None or action.y is None:
                return None
        return action

    def run(self) -> int:
        count = 0
        while self.config.max_frames is None or count < self.config.max_frames:
            image = self._capture(count)
            observation = self.observer(image)
            action = self._action_for_observation(observation, image)

            if action is None:
                return count + 1

            if self.config.dry_run:
                result = self.executor.propose(action)
            else:
                result = self.executor.execute(action)

            if not result.accepted:
                return count + 1

            count += 1
            if self.config.max_frames is None or count < self.config.max_frames:
                self.sleep(self.config.interval_seconds)

        return count


def run_live_control(
    objective: str,
    *,
    frames: int = 20,
    interval: float = 0.25,
    dismount_key: str = "a",
    target_x: float | None = None,
    target_y: float | None = None,
    live: bool = False,
    output: str | Path = "screenshots/live",
) -> int:
    """Run the controlled loop against the current desktop."""
    objective_model = Objective(objective)
    config = LiveControlConfig(
        interval_seconds=interval,
        max_frames=frames,
        dry_run=not live,
        dismount_key=dismount_key,
        target_x=target_x,
        target_y=target_y,
        save_frames=True,
        output_dir=Path(output),
    )
    source = Desktop(dry_run=True)
    observer = AlbionControlObserver(
        objective_model,
        target_x=target_x,
        target_y=target_y,
    )
    executor = PyAutoGUIExecutor(dry_run=config.dry_run)
    return LiveControlRuntime(
        source,
        observer,
        executor,
        objective_model,
        config,
    ).run()


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled Albion gathering-agent loop")
    parser.add_argument("--objective", default="fiber", choices=("leather", "fiber", "ore", "wood", "stone"))
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--dismount-key", default="a")
    parser.add_argument("--target-x", type=float)
    parser.add_argument("--target-y", type=float)
    parser.add_argument("--output", type=Path, default=Path("screenshots/live"))
    parser.add_argument("--live", action="store_true", help="enable real mouse/keyboard input")
    args = parser.parse_args()

    if args.live:
        print("LIVE CONTROL ENABLED: Albion must be the active window.")
    else:
        print("Dry-run mode: no mouse or keyboard input will be sent.")

    count = run_live_control(
        args.objective,
        frames=args.frames,
        interval=args.interval,
        dismount_key=args.dismount_key,
        target_x=args.target_x,
        target_y=args.target_y,
        live=args.live,
        output=args.output,
    )
    print(f"control_frames={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
