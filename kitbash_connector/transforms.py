"""Connector alignment, connection lifecycle, and pivot mathematics."""

import uuid
from typing import Any, Optional

import bpy
from mathutils import Matrix, Quaternion, Vector

from . import utils


EPSILON = 1.0e-7


def translate_about_pivot(
    matrix_world: Matrix,
    pivot: Vector,
    rotation: Quaternion,
) -> Matrix:
    """Rotate a world matrix around a fixed world-space pivot."""
    return (
        Matrix.Translation(pivot)
        @ rotation.to_matrix().to_4x4()
        @ Matrix.Translation(-pivot)
        @ matrix_world
    )


def align_connector_pair(
    scene: bpy.types.Scene,
    obj_a: bpy.types.Object,
    connector_a: Any,
    obj_b: bpy.types.Object,
    connector_b: Any,
) -> Any:
    """Align object B to object A and create or reactivate a connection."""
    if obj_a == obj_b:
        raise ValueError("Choose connectors on two different objects.")
    existing = utils.pair_connection(
        scene,
        obj_a,
        connector_a.connector_id,
        obj_b,
        connector_b.connector_id,
    )
    if existing is not None and existing.is_connected:
        raise ValueError("These connector points are already connected.")

    active_a = utils.connection_for(
        scene,
        obj_a,
        connector_a.connector_id,
        active_only=True,
    )
    active_b = utils.connection_for(
        scene,
        obj_b,
        connector_b.connector_id,
        active_only=True,
    )
    if active_a is not None or active_b is not None:
        raise ValueError("One or both selected connectors are already in use.")

    pivot = utils.connector_world_position(obj_a, connector_a).copy()
    movable_anchor = utils.connector_world_position(obj_b, connector_b)
    obj_b.matrix_world = (
        Matrix.Translation(pivot - movable_anchor) @ obj_b.matrix_world
    )

    connection = existing
    if connection is None:
        connection = scene.kitbash_connections.add()
        connection.connection_id = uuid.uuid4().hex
    connection.object_a = obj_a
    connection.object_b = obj_b
    connection.connector_a_id = connector_a.connector_id
    connection.connector_b_id = connector_b.connector_id
    connection.shared_position = pivot
    connection.baseline_rotation_a = tuple(obj_a.matrix_world.to_quaternion())
    connection.baseline_rotation_b = tuple(obj_b.matrix_world.to_quaternion())
    connection.is_connected = True
    connector_a.connection_state = "Connected"
    connector_b.connection_state = "Connected"
    bpy.context.view_layer.update()
    utils.redraw_viewports()
    return connection


def disconnect_connection(scene: bpy.types.Scene, connection: Any) -> None:
    """Deactivate a connection without changing either object's transform."""
    connection.is_connected = False
    for obj, connector_id in utils.connection_endpoints(connection):
        connector = utils.connector_by_id(obj, connector_id)
        if connector is not None:
            connector.connection_state = "Disconnected"
    utils.redraw_viewports()


def reconnect_connection(scene: bpy.types.Scene, connection: Any) -> None:
    """Realign and reactivate a disconnected connection."""
    if connection.is_connected:
        raise ValueError("This connection is already active.")
    obj_a = connection.object_a
    obj_b = connection.object_b
    if obj_a is None or obj_b is None:
        raise ValueError("One of the connected objects is missing.")
    connector_a = utils.connector_by_id(obj_a, connection.connector_a_id)
    connector_b = utils.connector_by_id(obj_b, connection.connector_b_id)
    if connector_a is None or connector_b is None:
        raise ValueError("One of the connected anchors is missing.")
    align_connector_pair(scene, obj_a, connector_a, obj_b, connector_b)


def rotate_about_connector(
    obj: bpy.types.Object,
    original_matrix: Matrix,
    pivot: Vector,
    rotation: Quaternion,
) -> None:
    """Apply a pivot rotation to an object's original world matrix."""
    obj.matrix_world = translate_about_pivot(original_matrix, pivot, rotation)


def pivot_for_object(
    scene: bpy.types.Scene,
    obj: bpy.types.Object,
    connector: Any,
) -> tuple[Vector, Any]:
    """Return the fixed world pivot and active relationship for a connector."""
    connection = utils.connection_for(
        scene,
        obj,
        connector.connector_id,
        active_only=True,
    )
    if connection is None:
        raise ValueError("This connector is not connected.")
    return Vector(connection.shared_position), connection


def reset_object_rotation(
    scene: bpy.types.Scene,
    obj: bpy.types.Object,
    connector: Any,
) -> None:
    """Restore an endpoint to its orientation at connection/reconnection time."""
    pivot, connection = pivot_for_object(scene, obj, connector)
    current_rotation = obj.matrix_world.to_quaternion()
    if connection.object_a == obj:
        target = Quaternion(connection.baseline_rotation_a)
    else:
        target = Quaternion(connection.baseline_rotation_b)
    corrective_rotation = target @ current_rotation.inverted()
    obj.matrix_world = translate_about_pivot(
        obj.matrix_world,
        pivot,
        corrective_rotation,
    )
    utils.redraw_viewports()


_applying_constraints = False


def preserve_connections(scene: bpy.types.Scene) -> None:
    """Translate active endpoints back to their stored shared pivots."""
    global _applying_constraints
    if _applying_constraints:
        return
    _applying_constraints = True
    changed = False
    try:
        for connection in scene.kitbash_connections:
            if not connection.is_connected:
                continue
            endpoints = list(utils.connection_endpoints(connection))
            if len(endpoints) != 2:
                connection.is_connected = False
                continue
            pivot = Vector(connection.shared_position)
            for obj, connector_id in endpoints:
                connector = utils.connector_by_id(obj, connector_id)
                if connector is None:
                    connection.is_connected = False
                    continue
                current = utils.connector_world_position(obj, connector)
                delta = pivot - current
                if delta.length > EPSILON:
                    obj.matrix_world = (
                        Matrix.Translation(delta) @ obj.matrix_world
                    )
                    changed = True
        if changed:
            bpy.context.view_layer.update()
    finally:
        _applying_constraints = False
