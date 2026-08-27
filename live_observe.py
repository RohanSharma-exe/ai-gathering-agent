"""Capture and inspect live desktop frames without sending game input.

This is the calibration bridge between the tested perception code and a real
Albion window. It intentionally performs no mouse/keyboard actions.
"""

from __future__ import annotations

import argparse
import ctypes
from pathlib import Path

from albion_perception import AlbionUIObserver
from desktop import Desktop
from observation import UIObservation
from runtime import ObservationRuntime, RuntimeConfig


_observer = AlbionUIObserver()


def _albion_client_rect() -> tuple[int, int, int, int] | None:
    """Return the Albion client-area rectangle on Windows, if visible."""
    if not hasattr(ctypes, "windll"):
        return None

    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "Albion Online Client")
    if not hwnd:
        return None

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    client = RECT()
    origin = POINT()
    if not user32.GetClientRect(hwnd, ctypes.byref(client)):
        return None
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None

    left = origin.x
    top = origin.y
    right = left + (client.right - client.left)
    bottom = top + (client.bottom - client.top)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def observe_frame(image: object) -> UIObservation:
    """Interpret the Albion client portion of one desktop screenshot."""
    if not hasattr(image, "size") or not hasattr(image, "crop"):
        raise TypeError("expected a Pillow-compatible screenshot image")

    rect = _albion_client_rect()
    if rect is not None:
        left, top, right, bottom = rect
        screen_width, screen_height = image.size
        left = max(0, min(left, screen_width - 1))
        top = max(0, min(top, screen_height - 1))
        right = max(left + 1, min(right, screen_width))
        bottom = max(top + 1, min(bottom, screen_height))
        image = image.crop((left, top, right, bottom))

    return _observer.observe(image)


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
