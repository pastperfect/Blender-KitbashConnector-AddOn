"""Shared connector lookup and coordinate conversion helpers."""

from typing import Any, Iterable, Optional

import bpy
from mathutils import Vector


def redraw_viewports() -> None:
    """Request redraws for all visible 3D viewports."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def connector_by_id(obj: bpy.types.Object, connector_id: str) -> Optional[Any]:
    """Return a connector by stable ID, if it exists."""
    return next(
        (
            connector
            for connector in obj.kitbash_connectors
            if connector.connector_id == connector_id
        ),
        None,
    )


def active_connector(obj: Optional[bpy.types.Object]) -> Optional[Any]:
    """Return the selected connector on an object."""
    if obj is None:
        return None
    connectors = obj.kitbash_connectors
    if 0 <= obj.kitbash_active_connector < len(connectors):
        return connectors[obj.kitbash_active_connector]
    return None


def connector_world_position(
    obj: bpy.types.Object,
    connector: Any,
) -> Vector:
    """Convert a connector's local position to world space."""
    return obj.matrix_world @ Vector(connector.local_position)


def connector_world_normal(
    obj: bpy.types.Object,
    connector: Any,
) -> Vector:
    """Convert a local normal with the inverse-transpose world transform."""
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    normal = normal_matrix @ Vector(connector.local_normal)
    return normal.normalized()


def world_to_local_position(
    obj: bpy.types.Object,
    position: Vector,
) -> Vector:
    """Convert a world point to the object's local coordinates."""
    return obj.matrix_world.inverted() @ position


def world_to_local_normal(
    obj: bpy.types.Object,
    normal: Vector,
) -> Vector:
    """Convert a world normal to local coordinates for this transform."""
    local_normal = obj.matrix_world.to_3x3().transposed() @ normal
    return local_normal.normalized()


def connection_for(
    scene: bpy.types.Scene,
    obj: bpy.types.Object,
    connector_id: str,
    *,
    active_only: bool = False,
) -> Optional[Any]:
    """Find the relationship containing a connector."""
    for connection in scene.kitbash_connections:
        if active_only and not connection.is_connected:
            continue
        matches_a = (
            connection.object_a == obj
            and connection.connector_a_id == connector_id
        )
        matches_b = (
            connection.object_b == obj
            and connection.connector_b_id == connector_id
        )
        if matches_a or matches_b:
            return connection
    return None


def pair_connection(
    scene: bpy.types.Scene,
    obj_a: bpy.types.Object,
    connector_a_id: str,
    obj_b: bpy.types.Object,
    connector_b_id: str,
) -> Optional[Any]:
    """Find a connection between this ordered or reversed connector pair."""
    for connection in scene.kitbash_connections:
        forward = (
            connection.object_a == obj_a
            and connection.connector_a_id == connector_a_id
            and connection.object_b == obj_b
            and connection.connector_b_id == connector_b_id
        )
        reverse = (
            connection.object_a == obj_b
            and connection.connector_a_id == connector_b_id
            and connection.object_b == obj_a
            and connection.connector_b_id == connector_a_id
        )
        if forward or reverse:
            return connection
    return None


def selected_mesh_objects(context: bpy.types.Context) -> list[bpy.types.Object]:
    """Return selected mesh objects in stable collection order."""
    return [
        obj
        for obj in context.scene.objects
        if obj.select_get() and obj.type == "MESH"
    ]


def connection_endpoints(
    connection: Any,
) -> Iterable[tuple[bpy.types.Object, str]]:
    """Yield the two object and connector ID endpoints."""
    if connection.object_a is not None:
        yield connection.object_a, connection.connector_a_id
    if connection.object_b is not None:
        yield connection.object_b, connection.connector_b_id
