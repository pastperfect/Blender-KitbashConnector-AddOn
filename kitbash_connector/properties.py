"""Persistent connector and connection property definitions."""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Object, PropertyGroup, Scene


_updating_depth = False


def _update_connection_depth(
    connection: "KitbashConnection",
    context: bpy.types.Context,
) -> None:
    """Apply a changed depth slider to the active connection."""
    global _updating_depth
    if _updating_depth or (
        not connection.is_connected
        or connection.object_a is None
        or connection.object_b is None
    ):
        return
    from . import transforms

    limit = context.scene.kitbash_settings.depth_limit
    requested_depth = max(-limit, min(limit, connection.depth_offset))
    _updating_depth = True
    try:
        connection.depth_offset = requested_depth
        transforms.set_connection_depth(connection, requested_depth)
    finally:
        _updating_depth = False


class KitbashConnectorPoint(PropertyGroup):
    """An anchor stored in its parent object's local coordinate system."""

    connector_id: StringProperty(
        name="Connector ID",
        description="Stable identifier for this connector",
    )
    label: StringProperty(
        name="Label",
        description="Human-readable connector name",
        default="Connector",
    )
    local_position: FloatVectorProperty(
        name="Local Position",
        description="Anchor position in the parent object's local space",
        subtype="XYZ",
        size=3,
        precision=6,
    )
    local_normal: FloatVectorProperty(
        name="Local Normal",
        description="Surface normal in the parent object's local space",
        subtype="XYZ",
        size=3,
        precision=6,
        default=(0.0, 0.0, 1.0),
    )
    visual_size: FloatProperty(
        name="Connector Size",
        description="Viewport marker size captured when the connector was placed",
        min=0.001,
        max=1.0,
        default=0.08,
    )
    connection_state: StringProperty(
        name="Connection State",
        description="Current connector connection state",
        default="Available",
    )


class KitbashConnection(PropertyGroup):
    """A relationship between two connector points."""

    connection_id: StringProperty(name="Connection ID")
    object_a: PointerProperty(name="Object A", type=Object)
    object_b: PointerProperty(name="Object B", type=Object)
    connector_a_id: StringProperty(name="Connector A")
    connector_b_id: StringProperty(name="Connector B")
    shared_position: FloatVectorProperty(
        name="Shared Position",
        subtype="XYZ",
        size=3,
        precision=7,
    )
    baseline_rotation_a: FloatVectorProperty(
        name="Object A Baseline Rotation",
        subtype="QUATERNION",
        size=4,
        default=(1.0, 0.0, 0.0, 0.0),
    )
    baseline_rotation_b: FloatVectorProperty(
        name="Object B Baseline Rotation",
        subtype="QUATERNION",
        size=4,
        default=(1.0, 0.0, 0.0, 0.0),
    )
    is_connected: BoolProperty(
        name="Connected",
        description="Whether this relationship is actively constrained",
        default=True,
    )
    depth_offset: FloatProperty(
        name="Push In / Pull Out",
        description="Slide the attached part along the connection direction",
        subtype="DISTANCE",
        min=-0.1,
        max=0.1,
        soft_min=-0.005,
        soft_max=0.005,
        step=1,
        precision=3,
        default=0.0,
        update=_update_connection_depth,
    )
    applied_depth_offset: FloatProperty(
        name="Applied Depth",
        subtype="DISTANCE",
        default=0.0,
        options={"HIDDEN"},
    )


class KitbashSettings(PropertyGroup):
    """Scene-level display and placement settings."""

    show_connectors: BoolProperty(
        name="Show Connectors",
        description="Display connector markers in the 3D viewport",
        default=True,
    )
    visual_size: FloatProperty(
        name="Connector Visual Size",
        description="Viewport marker diameter in display units",
        min=0.001,
        max=1.0,
        default=0.08,
    )
    display_color: FloatVectorProperty(
        name="Connector Display Colour",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 0.35, 0.08),
    )
    snap_precision: IntProperty(
        name="Snap Precision",
        description="Number of local-coordinate decimal places retained",
        min=0,
        max=8,
        default=6,
    )
    show_connection_lines: BoolProperty(
        name="Show Connection Lines",
        description="Draw lines between connected anchors",
        default=True,
    )
    show_surface_normals: BoolProperty(
        name="Show Surface Normals",
        description="Draw connector surface-normal directions",
        default=False,
    )
    depth_limit: FloatProperty(
        name="Push/Pull Limit",
        description="Maximum guided depth adjustment in scene units",
        subtype="DISTANCE",
        min=0.0001,
        max=0.1,
        soft_min=0.001,
        soft_max=0.02,
        precision=3,
        default=0.005,
    )


CLASSES = (
    KitbashConnectorPoint,
    KitbashConnection,
    KitbashSettings,
)


def register() -> None:
    """Register property classes and attach them to Blender data."""
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    Object.kitbash_connectors = CollectionProperty(type=KitbashConnectorPoint)
    Object.kitbash_active_connector = IntProperty(
        name="Active Connector",
        min=0,
        default=0,
    )
    Scene.kitbash_connections = CollectionProperty(type=KitbashConnection)
    Scene.kitbash_settings = PointerProperty(type=KitbashSettings)


def unregister() -> None:
    """Detach scene and object properties and unregister their classes."""
    del Scene.kitbash_settings
    del Scene.kitbash_connections
    del Object.kitbash_active_connector
    del Object.kitbash_connectors
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

