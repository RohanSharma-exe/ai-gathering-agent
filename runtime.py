"""Real-time observation loop for the local gathering-agent prototype.

This module intentionally stops at perception/logging. It does not execute
mouse or keyboard actions, making the first live-game test safe to run while
we calibrate the visual pipeline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from desktop import Desktop
from observation import UIObservation


class FrameSource(Protocol):
    def screenshot(self, path: str | Path | None = None) -> object: ...


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for the observation-only loop."""

    interval_seconds: float = 0.25
    max_frames: int | None = None
    save_frames: bool = False
    output_dir: Path = Path("screenshots/live")

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if self.max_frames is not None and self.max_frames < 1:
            raise ValueError("max_frames must be positive when provided")


@dataclass(frozen=True)
class RuntimeFrame:
    """One captured frame and its derived observation."""

    index: int
    observation: UIObservation
    image: object


class ObservationRuntime:
    """Capture frames and pass them through a supplied local observer.

    ``observer`` is deliberately injected so the runtime can later use a
    classical detector, a local ML model, or an occasional vision API call
    without changing the loop itself.
    """

    def __init__(
        self,
        source: FrameSource,
        observer: Callable[[object], UIObservation],
        config: RuntimeConfig | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self.observer = observer
        self.config = config or RuntimeConfig()
        self.sleep = sleep

    def capture_once(self, index: int) -> RuntimeFrame:
        path: Path | None = None
        if self.config.save_frames:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.config.output_dir / f"frame_{index:06d}.png"
        image = self.source.screenshot(path)
        return RuntimeFrame(index=index, observation=self.observer(image), image=image)

    def run(self, on_frame: Callable[[RuntimeFrame], None] | None = None) -> int:
        """Run until ``max_frames`` is reached; return captured frame count."""
        count = 0
        while self.config.max_frames is None or count < self.config.max_frames:
            frame = self.capture_once(count)
            if on_frame is not None:
                on_frame(frame)
            count += 1
            if self.config.max_frames is None or count < self.config.max_frames:
                self.sleep(self.config.interval_seconds)
        return count


def run_live_observation(
    observer: Callable[[object], UIObservation],
    *,
    interval_seconds: float = 0.25,
    max_frames: int | None = 20,
    save_frames: bool = True,
    output_dir: str | Path = "screenshots/live",
) -> int:
    """Convenience entry point using the desktop screenshot adapter."""
    runtime = ObservationRuntime(
        Desktop(dry_run=True),
        observer,
        RuntimeConfig(
            interval_seconds=interval_seconds,
            max_frames=max_frames,
            save_frames=save_frames,
            output_dir=Path(output_dir),
        ),
    )
    return runtime.run()
