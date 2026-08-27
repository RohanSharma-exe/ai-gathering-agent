# Visual Calibration — Reference Screenshot

Reference image: user-provided Albion Online gameplay screenshot.

## Image characteristics

- Resolution: 1017 × 761 pixels.
- The central playfield occupies most of the frame.
- HUD elements are distributed around the edges.

## Stable visual regions observed

These are **observation regions only**. They are intentionally represented as normalized rectangles so they can be adapted to other resolutions.

| Region | Approximate normalized rectangle `(x, y, width, height)` | Purpose |
|---|---|---|
| Playfield | `(0.00, 0.00, 1.00, 0.90)` | Main world observation |
| Player/status | `(0.00, 0.00, 0.22, 0.15)` | Character/status UI |
| Quest/objective | `(0.83, 0.00, 0.17, 0.20)` | Objective/status UI |
| Minimap | `(0.78, 0.68, 0.22, 0.25)` | Local map observation |
| Action bar | `(0.25, 0.90, 0.52, 0.10)` | Action/status observation |

## Important calibration decision

Do not use fixed pixel coordinates for perception. The detector should work with normalized regions and convert to pixels only after the screenshot dimensions are known.

The reference screenshot does **not** show the inventory panel open, so no inventory-panel coordinates are inferred from it. Inventory detection should be calibrated from a separate screenshot when that UI is visible.

Likewise, a single screenshot is insufficient to infer reliable object-detection rules for animals, resources, combat state, or mounted state. Those should be treated as separate perception classes rather than guessed from color or position.

## Next perception milestone

Implement local, screenshot-only feature extraction and confidence scoring for the stable UI regions first. Then add controlled test fixtures for individual visual classes. Keep the planner independent from the implementation of perception.
