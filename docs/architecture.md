# Architecture

## Data ownership

Each mesh object owns a collection of `KitbashConnectorPoint` values:

- stable connector ID and display label;
- local-space point and surface normal;
- captured display size;
- connection-state text.

Object-local storage is intentional. A connector follows an object's complete
matrix without reacting to evaluated mesh topology or changing vertex data.
Scene-level `KitbashConnection` values contain the two object pointers,
connector IDs, shared world-space pivot, endpoint baseline quaternions,
active/disconnected state, and applied push/pull depth. Connector metadata,
object matrices, and actual mesh geometry remain separate concepts.

## Placement

`placement.py` creates a 3D ray from the viewport's mouse coordinate with
`region_2d_to_origin_3d` and `region_2d_to_vector_3d`. `Scene.ray_cast`
evaluates the dependency graph, and placement is accepted only when the hit
belongs to the active mesh.

Points use the inverse object matrix. For normals, local-to-world uses the
inverse transpose of the linear matrix:

```text
world_normal = normalize((A^-1)^T * local_normal)
```

Converting the evaluated world-space hit back to local space uses:

```text
local_normal = normalize(A^T * world_normal)
```

This is necessary for objects with non-uniform scale. A plain inverse or a
rotation-only conversion gives incorrect normal direction in that case.

## Cutting transaction

`cutting.py` builds two BMesh copies from the object's evaluated mesh. It uses
`bisect_plane` with opposite clear-side arguments, fills boundary edges on the
cut plane where possible, validates each resulting mesh, and only then links
two result objects into the source object's collections.

The source remains unchanged throughout construction. It is hidden after
success when **Keep Original** is enabled. Any failure before commit removes
temporary objects and mesh data. Existing connectors are classified onto the
side containing their local point, and a fresh connector pair is created from
the cut-boundary centroid with opposite world normals.

## Alignment and pivot rotation

Connecting obtains both world anchors. It left-multiplies the active/second
object's matrix by `T(anchor_a - anchor_b)`. Translation in world space avoids
coupling the offset to that object's scale or orientation.

The guided workflow can first rotate the movable anchor about its own world
position so its normal faces the target normal. Existing manual connections
retain their original position-only behaviour.

Rotation is applied as:

```text
new_matrix = T(pivot) * R * T(-pivot) * original_matrix
```

The operation never changes `object.origin`; it transforms the full object
matrix. The active connector remains numerically fixed for all angles and
independent of the object's scale and origin.

Push/pull translates the movable object along the target normal and recomputes
the movable connector's local position so its world anchor remains at the
shared pivot. Mesh vertices are unchanged.

## Guided assembly state

The Stick Parts Together operator holds the pending source hit in operator
state until the user chooses a target. Cancelling either stage therefore leaves
connector collections unchanged. Mouse movement uses non-mutating transform
previews. The source and optional target connector are committed only after
the final click.

Viewport drawing highlights target points as available, selected, or already in
use. A transformed local bounding box previews which object will move and where
it will land.

## Constraint pass

Active connection records retain one immutable shared pivot. A lightweight
dependency-graph handler detects changed endpoint positions and translates the
endpoint back to that pivot. This maintains a hinge during Blender's normal
move and rotate interaction. Disconnected relationships are ignored until
reconnected.

Connections on distinct connector pairs can coexist. A single rigid object can
represent physically compatible branches, but cyclic or contradictory
multi-pivot arrangements are overconstrained. The user should disconnect or
avoid those incompatible joints.

## Module boundaries

- `properties.py`: Blender RNA-backed persistence.
- `cutting.py`: transactional BMesh separation, capping, and connector
  generation.
- `placement.py`: viewport ray casting and local data creation.
- `transforms.py`: connection lifecycle, normal alignment, and matrix
  mathematics.
- `visuals.py`: GPU viewport drawing and constraint registration.
- `operators.py`: modal placement and rotation plus management operations.
- `panel.py`: N-panel controls and connector list.
- `utils.py`: shared lookups and coordinate conversion.
