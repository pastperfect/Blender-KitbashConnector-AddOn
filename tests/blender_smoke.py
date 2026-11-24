"""Headless Blender smoke tests for Kitbash Connector."""

import math
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Matrix, Quaternion, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import kitbash_connector  # noqa: E402
from kitbash_connector import transforms, utils  # noqa: E402


TOLERANCE = 1.0e-5


def assert_near(
    actual: Vector,
    expected: Vector,
    message: str,
) -> None:
    """Assert that two vectors are equal within the test tolerance."""
    distance = (actual - expected).length
    if distance > TOLERANCE:
        raise AssertionError(
            f"{message}: distance {distance} exceeds {TOLERANCE}",
        )


def add_cube(name: str, location: tuple[float, float, float]) -> bpy.types.Object:
    """Create and return a cube for smoke testing."""
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    return obj


def add_point(
    obj: bpy.types.Object,
    connector_id: str,
    position: tuple[float, float, float],
    normal: tuple[float, float, float],
) -> Any:
    """Add a manually defined connector for deterministic testing."""
    connector = obj.kitbash_connectors.add()
    connector.connector_id = connector_id
    connector.label = connector_id
    connector.local_position = position
    connector.local_normal = normal
    obj.kitbash_active_connector = len(obj.kitbash_connectors) - 1
    return connector


def run_tests() -> None:
    """Run transform and lifecycle assertions in a factory scene."""
    kitbash_connector.register()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    obj_a = add_cube("Anchor A", (2.0, 0.0, 0.0))
    obj_b = add_cube("Anchor B", (-4.0, 1.5, 3.0))
    obj_b.scale = (1.5, 0.75, 2.25)
    obj_b.rotation_euler = (0.3, -0.4, 0.8)
    bpy.context.view_layer.update()

    connector_a = add_point(obj_a, "a", (1.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    connector_b = add_point(obj_b, "b", (-1.0, 0.0, 0.0), (-1.0, 0.0, 0.0))
    connection = transforms.align_connector_pair(
        scene,
        obj_a,
        connector_a,
        obj_b,
        connector_b,
    )
    anchor_a = utils.connector_world_position(obj_a, connector_a)
    anchor_b = utils.connector_world_position(obj_b, connector_b)
    assert_near(anchor_a, anchor_b, "Connector alignment")

    expected_normal = utils.connector_world_normal(obj_b, connector_b)
    if abs(expected_normal.length - 1.0) > TOLERANCE:
        raise AssertionError("World normal is not normalized.")

    pivot = Vector(connection.shared_position)
    original = obj_b.matrix_world.copy()
    transforms.rotate_about_connector(
        obj_b,
        original,
        pivot,
        Quaternion((0.0, 0.0, 1.0), math.tau),
    )
    assert_near(
        utils.connector_world_position(obj_b, connector_b),
        pivot,
        "360-degree pivot rotation",
    )

    obj_b.matrix_world = (
        Matrix.Translation((3.0, -2.0, 1.0))
        @ obj_b.matrix_world
    )
    transforms.preserve_connections(scene)
    assert_near(
        utils.connector_world_position(obj_b, connector_b),
        pivot,
        "Move constraint preservation",
    )

    transforms.reset_object_rotation(scene, obj_b, connector_b)
    assert (
        obj_b.matrix_world.to_quaternion().rotation_difference(
            Quaternion(connection.baseline_rotation_b),
        ).angle
        < TOLERANCE
    ), "Reset rotation did not restore the connection baseline."

    original_location = obj_b.matrix_world.translation.copy()
    transforms.disconnect_connection(scene, connection)
    obj_b.matrix_world = (
        Matrix.Translation((2.0, 0.0, 0.0)) @ obj_b.matrix_world
    )
    bpy.context.view_layer.update()
    if (obj_b.matrix_world.translation - original_location).length < TOLERANCE:
        raise AssertionError("Disconnect did not permit independent movement.")

    transforms.reconnect_connection(scene, connection)
    assert connection.is_connected
    assert_near(
        utils.connector_world_position(obj_a, connector_a),
        utils.connector_world_position(obj_b, connector_b),
        "Reconnect alignment",
    )

    try:
        transforms.align_connector_pair(
            scene,
            obj_a,
            connector_a,
            obj_b,
            connector_b,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate active connection was accepted.")

    obj_c = add_cube("Anchor C", (1.0, 4.0, -2.0))
    connector_b_child = add_point(
        obj_b,
        "b-child",
        (1.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
    )
    connector_c = add_point(
        obj_c,
        "c",
        (-1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
    )
    transforms.align_connector_pair(
        scene,
        obj_b,
        connector_b_child,
        obj_c,
        connector_c,
    )
    assert_near(
        utils.connector_world_position(obj_b, connector_b_child),
        utils.connector_world_position(obj_c, connector_c),
        "Three-object chain alignment",
    )
    if len(scene.kitbash_connections) != 2:
        raise AssertionError("Multiple scene connections were not retained.")

    kitbash_connector.unregister()
    print("KITBASH_SMOKE_OK")


if __name__ == "__main__":
    run_tests()
