# Changelog

## [1.1.5] - 2026-11-24

### Fixed

- Draw essential connected-part controls before the optional Rotation Dial, so
  a dial registration problem cannot hide Flip, Move Point, Remove Point, or
  Push/Pull.

## [1.1.4] - 2026-11-24

### Fixed

- Replaced the Rotation Dial's enum-property assignment with a dedicated
  operator so a stale Blender RNA definition cannot truncate the ADJUST
  panel.

## [1.1.3] - 2026-11-24

### Fixed

- ADJUST controls now remain available when either connected object is
  selected, regardless of the connector-list selection.
- Rotation, flip, disconnect, move, remove, and depth controls resolve the
  selected object's active connection automatically.

## [1.1.2] - 2026-11-24

### Fixed

- Preserved mouse-move events during middle-button camera drags, completing
  orbit and pan support inside active connector workflows.

## [1.1.1] - 2026-11-24

### Fixed

- Allowed viewport orbit, pan, and zoom gestures while Stick Parts Together is
  active.
- Kept connected anchors visible and distinct from available connectors.

### Added

- Move Connection Point to reposition an active anchor on the connected
  object's visible surface while preserving its shared pivot.
- Direct Move Point and Remove Point controls in the adjustment panel.

## [1.1.0] - 2026-11-24

### Added

- Guided Stick Parts Together workflow with automatic source and optional
  target connector placement.
- Available, selected, and in-use connector highlighting with a movable-part
  alignment preview.
- Face-to-face normal alignment for guided assembly.
- Rotation dial, fixed -90/-15/+15/+90 degree controls, flip, and -5 mm to
  +5 mm push/pull adjustment.
- Beginner-oriented ASSEMBLE and ADJUST panel sections with advanced controls
  retained.

## [1.0.0] - 2026-11-24

### Added

- Initial modular Blender add-on for local-space connector placement.
- Surface ray casting with viewport preview markers.
- Exact selected-anchor alignment and active hinge constraints.
- World-axis and free pivot rotation with reset support.
- Disconnect, reconnect, multiple scene connections, and undo-enabled
  operators.
- Connector, connection-line, and normal visualisation.
- Blender 4.2+ extension manifest, installation package build script, and user
  guide.
