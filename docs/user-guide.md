# Kitbash Connector User Guide

## Guided assembly

### Stick Parts Together

1. Select the part that should move.
2. Click **Stick Parts Together**.
3. Click a visible face on that part. Green preview markers show valid surface
   hits.
4. Hover over another mesh. Green points are available, blue is the currently
   selected point, and red points are already in use.
5. Click an available point. If there is no nearby point, click the desired
   target surface and Kitbash Connector creates one.
6. The moving part is rotated to face the target and both new points are
   aligned automatically.

Middle-mouse orbit and pan, mouse-wheel zoom, trackpad gestures, and numpad view
navigation remain available while this workflow is active.

Escape or right-click cancels either stage without creating connector data.
Existing connector points and scene connections are unchanged.

### Simple adjustment controls

After connecting, select either endpoint object and use **ADJUST**. You do not
need to select a connector row manually:

- Use the -90, -15, +15, and +90 degree buttons for repeatable rotation.
- Drag **Rotation Dial** and left-click to confirm. Escape or right-click
  restores the starting transform.
- **Flip** turns the attached object 180 degrees while retaining its pivot.
- **Push In / Pull Out** slides the moving part over a -5 mm to +5 mm range.
  Blender scene units determine the displayed distance. Change **Push/Pull
  Limit** in **ADVANCED** to use a different range.
- **Move Point** repositions the active connected anchor by clicking another
  visible surface on the same object. The connected object's transform changes
  so the new point remains at the shared attachment pivot.
- **Remove Point** removes the active anchor and its relationship.
- **Undo** reverses the latest operation.

Connected anchors are cyan, the selected anchor is blue, and other available
anchors use the configured connector colour. To avoid contradictory multi-joint
constraints, Move Point is disabled for an object with more than one active
connection; disconnect the other connection first.

Push/pull adjusts the moving connector's local offset, not the mesh vertices.
The connector and its shared world-space pivot remain attached.

## Placing a connector

1. Select one mesh.
2. Click **Place Connector** in the connector panel.
3. Move the cursor over a visible face. A green preview point appears only when
   the ray intersects the active mesh.
4. Left-click to store the connector. Escape or right-click cancels.
5. Select another connector from the object's list when an object has several.

Positions are stored in local object space. Moving, rotating, scaling, saving,
or reopening the scene does not detach a marker from its parent.

## Connecting two objects

1. Select two mesh objects that each have an active connector.
2. Select the two objects normally, making the object that should move active
   last.
3. Click **Connect Selected Anchors**.
4. The active object's transform changes so the selected anchors occupy the
   same world position. Geometry and the separate object identities are
   unchanged.

An active connector can belong to only one active connection. Additional
connector points on an object can form other joints.

## Rotation

Select either endpoint object and use:

- **Rotate X**, **Rotate Y**, or **Rotate Z** for a world-axis pivot.
- **Free Rotate** for two axes derived from the current viewport.
- **Reset Rotation** to restore the orientation saved by the most recent
  connect or reconnect operation.

The add-on's transform is equivalent to:

```text
T(pivot) * R * T(-pivot) * original_matrix
```

Because the pivot is in world space and is fixed during the transform, the
connector remains at the shared point. The add-on does not permanently change
the object's origin.

## Disconnect and reconnect

**Disconnect** leaves the objects in place and preserves the relationship for
later use. **Reconnect** realigns the pair and makes the constraint active
again. Removing a connector deletes relationships that reference it.

## Settings

- **Connector Visual Size** controls marker display size for new markers.
- **Connector Display Colour** controls the marker colour.
- **Snap Precision** is the number of decimal places retained in local
  coordinates after a ray hit.
- **Show Connection Lines** displays lines for active relationships.
- **Show Surface Normals** draws each connector normal in world space.

## Constraints and limitations

- Active joints are maintained by a dependency-graph handler. Translating or
  rotating a connected endpoint is corrected so that the anchor remains fixed.
- Blender's ordinary object transforms can only satisfy one rigid transform
  for an object. A mesh participating in contradictory multi-joint or cyclic
  constraints may be overconstrained; avoid forcing several fixed pivots to
  disagree. Normal tree-like kitbash assemblies are supported.
- Placement requires a visible surface of the active mesh; ray casting does not
  place anchors in empty space.
- Modifiers are evaluated for viewport ray casting. Connector coordinates still
  reference the original object's local transform and do not modify mesh data.
