# Implementation Milestone Log

## Milestone 0 - Repository audit

Status: complete before feature development.

- Audited all add-on modules, transform paths, viewport handlers, the Blender
  smoke test, build script, manifest, and existing documentation.
- Confirmed connector metadata is object-local, connection metadata is
  scene-local, and mesh geometry is never modified by assembly operations.
- Identified `operators.py`, `placement.py`, `transforms.py`, `visuals.py`,
  `properties.py`, `panel.py`, and `tests/blender_smoke.py` as Milestone 1
  surfaces.
- Chose to preserve position-only manual alignment and add normal-aware
  alignment only to the guided workflow.

## Milestone 1 - Improve the assembly experience

Status: complete and headless-validated.

- Added the two-stage Stick Parts Together modal workflow.
- Added generic mesh ray casting, screen-space connector selection, and
  available/in-use target highlighting.
- Deferred connector creation until final confirmation so cancellation leaves
  no partial connector data.
- Added face-to-face alignment and transformed bounding-box preview.
- Added a normal-axis rotation dial, fixed rotation buttons, flip, and a
  push/pull depth slider with a configurable default limit of 5 mm.
- Retained all existing advanced connector management and rotation controls.
- Added smoke assertions for normal alignment, depth anchoring, flip
  anchoring, and automatic connector placement.

Validation:

- Blender 5.0 headless smoke test completed with `KITBASH_SMOKE_OK`.
- Syntax checks passed for the changed Python modules and smoke test.
- `git diff --check` passed.
- A fresh `kitbash_connector-1.1.0.zip` was built from the updated package.
  The existing `kitbash_connector-1.0.0.zip` was preserved.
- The build script now derives the ZIP name from the manifest version and
  refuses to overwrite an existing release archive.
- Follow-up 1.1.1: enabled viewport navigation during Stick Parts Together,
  distinguished connected and selected anchors, and added a surface-based Move
  Point operation with direct adjustment-panel access.
- Version 1.1.1 was validated with the Blender 5.0 headless smoke suite and
  packaged as `kitbash_connector-1.1.1.zip` alongside 1.0.0 and 1.1.0.
- Version 1.1.2 contains the follow-up middle-button drag pass-through and was
  packaged separately as `kitbash_connector-1.1.2.zip`.
- Follow-up 1.1.3: the panel and adjustment operators now resolve the selected
  object's connected endpoint automatically, so changing the connector-list
  selection no longer hides ADJUST controls.
- Follow-up 1.1.4: Rotation Dial is a dedicated operator. This removes the
  runtime enum assignment that could stop connected-state panel drawing after
  the fixed-angle buttons.
- Follow-up 1.1.5: essential ADJUST controls are drawn before Rotation Dial.

Outstanding limitations:

- Highlighting and modal cursor behaviour still need interactive viewport QA
  in Blender; the automated test covers data and transform behaviour.
- Compatibility currently means "not already connected". Named connector
  categories and compatibility rules begin in Milestone 3.
- The minimum supported Blender 4.2 runtime was not available in this
  environment; headless validation was run with Blender 5.0.
