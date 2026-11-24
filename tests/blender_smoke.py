"""Headless Blender smoke tests for Kitbash Connector."""

import math
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import bpy
from mathutils import Matrix, Quaternion, Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import kitbash_connector  # noqa: E402
from kitbash_connector import panel, placement, transforms, utils  # noqa: E402


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


class SmokeLayout:
    """Minimal layout surface for exercising panel draw logic."""

    def box(self) -> "SmokeLayout":
        """Return a child layout."""
        return self

    def row(self, **_kwargs: Any) -> "SmokeLayout":
        """Return a row layout."""
        return self

    def label(self, **_kwargs: Any) -> None:
        """Accept a panel label."""

    def operator(self, _idname: str, **_kwargs: Any) -> Any:
        """Return a mutable operator-properties object."""
        return SimpleNamespace()

    def prop(self, *_args: Any, **_kwargs: Any) -> None:
        """Accept a panel property."""

    def template_list(self, *_args: Any, **_kwargs: Any) -> None:
        """Accept a connector list."""


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
        align_normals=True,
    )
    panel.KITBASH_PT_connector_panel.draw(
        SimpleNamespace(
            layout=SmokeLayout(),
            _connection_status=(
                panel.KITBASH_PT_connector_panel._connection_status
            ),
            _active_connection=(
                panel.KITBASH_PT_connector_panel._active_connection
            ),
        ),
        bpy.context,
    )
    spare_connector = add_point(
        obj_b,
        "b-spare",
        (0.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    active_connection, active_connector = utils.active_connection_endpoint(
        scene,
        obj_b,
    )
    if active_connection != connection or active_connector != connector_b:
        raise AssertionError(
            "Object selection did not resolve its connected endpoint.",
        )
    if spare_connector == active_connector:
        raise AssertionError("An unrelated available point became active.")
    anchor_a = utils.connector_world_position(obj_a, connector_a)
    anchor_b = utils.connector_world_position(obj_b, connector_b)
    assert_near(anchor_a, anchor_b, "Connector alignment")
    normal_a = utils.connector_world_normal(obj_a, connector_a)
    normal_b = utils.connector_world_normal(obj_b, connector_b)
    if abs(normal_a.dot(normal_b) + 1.0) > TOLERANCE:
        raise AssertionError("Connector normals were not aligned face-to-face.")

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

    before_depth = obj_b.matrix_world.translation.copy()
    transforms.set_connection_depth(connection, 0.002)
    assert_near(
        utils.connector_world_position(obj_b, connector_b),
        Vector(connection.shared_position),
        "Depth adjustment anchor preservation",
    )
    if abs(
        (obj_b.matrix_world.translation - before_depth).length - 0.002
    ) > TOLERANCE:
        raise AssertionError("Depth adjustment did not move the part two mm.")
    transforms.set_connection_depth(connection, 0.0)
    assert_near(
        utils.connector_world_position(obj_b, connector_b),
        Vector(connection.shared_position),
        "Depth reset anchor preservation",
    )
    connection.depth_offset = 0.01
    if abs(connection.depth_offset - scene.kitbash_settings.depth_limit) > (
        TOLERANCE
    ):
        raise AssertionError("The configured depth limit was not applied.")
    connection.depth_offset = 0.0

    moved_surface = Vector((4.0, 2.0, 3.0))
    transforms.move_connected_point(
        scene,
        connection,
        obj_b,
        connector_b,
        moved_surface,
        Vector((0.0, 1.0, 0.0)),
        snap_precision=6,
    )
    assert_near(
        utils.connector_world_position(obj_b, connector_b),
        Vector(connection.shared_position),
        "Moved connector anchor preservation",
    )
    assert connection.is_connected, "Moving a point disconnected the pair."

    transforms.flip_connected_object(
        obj_b,
        connector_b,
        Vector(connection.shared_position),
    )
    assert_near(
        utils.connector_world_position(obj_b, connector_b),
        Vector(connection.shared_position),
        "Flip anchor preservation",
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

    surface_point = Vector((0.0, 2.0, 0.0))
    before_count = len(obj_c.kitbash_connectors)
    automatic_connector = placement.add_connector(
        obj_c,
        surface_point,
        Vector((0.0, 1.0, 0.0)),
        visual_size=0.08,
        snap_precision=6,
    )
    if len(obj_c.kitbash_connectors) != before_count + 1:
        raise AssertionError("Automatic connector placement did not add a point.")
    assert_near(
        utils.connector_world_position(obj_c, automatic_connector),
        surface_point,
        "Automatic connector world placement",
    )

    kitbash_connector.unregister()
    print("KITBASH_SMOKE_OK")


if __name__ == "__main__":
    run_tests()
