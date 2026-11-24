"""Viewport drawing and dependency-graph connection constraints."""

from typing import Any, Optional

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

from . import transforms, utils


_DRAW_HANDLER: Optional[Any] = None
_PREVIEW_POSITION: Optional[Vector] = None
_PREVIEW_NORMAL: Optional[Vector] = None
_MATCH_OBJECT: Optional[bpy.types.Object] = None
_MATCH_CONNECTOR_ID: Optional[str] = None
_MOVABLE_OBJECT: Optional[bpy.types.Object] = None
_PREVIEW_MATRIX: Optional[Matrix] = None
_CUT_POSITION: Optional[Vector] = None
_CUT_NORMAL: Optional[Vector] = None
_CUT_RADIUS = 1.0


def set_preview(position: Optional[Vector], normal: Optional[Vector]) -> None:
    """Set the surface-placement preview point."""
    global _PREVIEW_POSITION, _PREVIEW_NORMAL
    _PREVIEW_POSITION = position.copy() if position is not None else None
    _PREVIEW_NORMAL = normal.copy() if normal is not None else None
    utils.redraw_viewports()


def set_match_preview(
    target: Optional[bpy.types.Object],
    selected_connector: Optional[Any],
    movable_object: Optional[bpy.types.Object] = None,
    preview_matrix: Optional[Matrix] = None,
) -> None:
    """Set target-connector highlighting and movable-object preview."""
    global _MATCH_OBJECT, _MATCH_CONNECTOR_ID
    global _MOVABLE_OBJECT, _PREVIEW_MATRIX
    _MATCH_OBJECT = target
    _MATCH_CONNECTOR_ID = (
        selected_connector.connector_id
        if selected_connector is not None
        else None
    )
    _MOVABLE_OBJECT = movable_object
    _PREVIEW_MATRIX = (
        preview_matrix.copy() if preview_matrix is not None else None
    )
    utils.redraw_viewports()


def set_cut_preview(
    position: Optional[Vector],
    normal: Optional[Vector],
    radius: float = 1.0,
) -> None:
    """Set the viewport cutting-plane preview."""
    global _CUT_POSITION, _CUT_NORMAL, _CUT_RADIUS
    _CUT_POSITION = position.copy() if position is not None else None
    _CUT_NORMAL = normal.normalized() if normal is not None else None
    _CUT_RADIUS = radius
    utils.redraw_viewports()


def _draw_points(points: list[Vector], color: tuple[float, float, float, float],
                 size: float) -> None:
    if not points:
        return
    shader = gpu.shader.from_builtin("POINT_UNIFORM_COLOR")
    batch = batch_for_shader(shader, "POINTS", {"pos": points})
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.point_size_set(max(2.0, size * 100.0))
    batch.draw(shader)


def _draw_lines(lines: list[Vector], color: tuple[float, float, float, float],
                width: float = 1.5) -> None:
    if len(lines) < 2:
        return
    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": lines})
    shader.bind()
    shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
    shader.uniform_float("lineWidth", width)
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_match_preview() -> None:
    if _MATCH_OBJECT is None:
        return
    available: list[Vector] = []
    incompatible: list[Vector] = []
    selected: list[Vector] = []
    scene = bpy.context.scene
    for connector in _MATCH_OBJECT.kitbash_connectors:
        position = utils.connector_world_position(_MATCH_OBJECT, connector)
        connection = utils.connection_for(
            scene,
            _MATCH_OBJECT,
            connector.connector_id,
            active_only=True,
        )
        if connection is not None:
            incompatible.append(position)
        elif connector.connector_id == _MATCH_CONNECTOR_ID:
            selected.append(position)
        else:
            available.append(position)
    size = scene.kitbash_settings.visual_size
    _draw_points(available, (0.2, 1.0, 0.35, 1.0), size * 1.35)
    _draw_points(incompatible, (1.0, 0.18, 0.12, 1.0), size * 1.35)
    _draw_points(selected, (0.2, 0.65, 1.0, 1.0), size * 1.7)

    if _MOVABLE_OBJECT is None or _PREVIEW_MATRIX is None:
        return
    bounds = [
        Vector(corner) for corner in _MOVABLE_OBJECT.bound_box
    ]
    edges = (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )
    preview_lines: list[Vector] = []
    for start, end in edges:
        preview_lines.extend(
            (
                _PREVIEW_MATRIX @ bounds[start],
                _PREVIEW_MATRIX @ bounds[end],
            ),
        )
    _draw_lines(preview_lines, (0.2, 0.65, 1.0, 0.85), 2.0)


def _draw_cut_preview() -> None:
    if _CUT_POSITION is None or _CUT_NORMAL is None:
        return
    normal = _CUT_NORMAL
    reference = Vector((0.0, 0.0, 1.0))
    if abs(normal.dot(reference)) > 0.9:
        reference = Vector((1.0, 0.0, 0.0))
    tangent = normal.cross(reference).normalized()
    bitangent = normal.cross(tangent).normalized()
    first = _CUT_POSITION + (tangent - bitangent) * _CUT_RADIUS
    second = _CUT_POSITION + (tangent + bitangent) * _CUT_RADIUS
    third = _CUT_POSITION + (-tangent + bitangent) * _CUT_RADIUS
    fourth = _CUT_POSITION + (-tangent - bitangent) * _CUT_RADIUS
    _draw_lines(
        [first, second, second, third, third, fourth, fourth, first],
        (1.0, 0.45, 0.1, 0.95),
        2.5,
    )
    _draw_lines(
        [
            _CUT_POSITION - normal * _CUT_RADIUS * 0.35,
            _CUT_POSITION + normal * _CUT_RADIUS * 0.35,
        ],
        (1.0, 0.75, 0.15, 1.0),
        2.0,
    )


def draw_connectors() -> None:
    """Draw connector points, normals, lines, and placement preview."""
    context = bpy.context
    scene = context.scene
    if scene is None or not hasattr(scene, "kitbash_settings"):
        return
    _draw_cut_preview()
    settings = scene.kitbash_settings
    if not settings.show_connectors:
        return

    marker_color = (*settings.display_color, 1.0)
    available_points: list[Vector] = []
    connected_points: list[Vector] = []
    selected_points: list[Vector] = []
    active_obj = context.active_object
    _connection, selected_connector = utils.active_connection_endpoint(
        scene,
        active_obj,
    )
    if selected_connector is None:
        selected_connector = utils.active_connector(active_obj)
    for obj in scene.objects:
        for connector in obj.kitbash_connectors:
            position = utils.connector_world_position(obj, connector)
            connection = utils.connection_for(
                scene,
                obj,
                connector.connector_id,
                active_only=True,
            )
            if obj == active_obj and connector == selected_connector:
                selected_points.append(position)
            elif connection is not None:
                connected_points.append(position)
            else:
                available_points.append(position)
            if settings.show_surface_normals:
                normal = utils.connector_world_normal(obj, connector)
                _draw_lines(
                    [
                        position,
                        position + normal * settings.visual_size * 4.0,
                    ],
                    (0.2, 0.85, 1.0, 1.0),
                )
    _draw_points(available_points, marker_color, settings.visual_size)
    _draw_points(
        connected_points,
        (0.2, 0.85, 1.0, 1.0),
        settings.visual_size * 1.2,
    )
    _draw_points(
        selected_points,
        (0.2, 0.65, 1.0, 1.0),
        settings.visual_size * 1.5,
    )
    _draw_match_preview()

    if _PREVIEW_POSITION is not None:
        _draw_points(
            [_PREVIEW_POSITION],
            (0.2, 1.0, 0.35, 1.0),
            settings.visual_size * 1.2,
        )
        if settings.show_surface_normals and _PREVIEW_NORMAL is not None:
            _draw_lines(
                [
                    _PREVIEW_POSITION,
                    _PREVIEW_POSITION
                    + _PREVIEW_NORMAL * settings.visual_size * 4.0,
                ],
                (0.2, 1.0, 0.35, 1.0),
            )

    if settings.show_connection_lines:
        line_points: list[Vector] = []
        for connection in scene.kitbash_connections:
            if not connection.is_connected:
                continue
            pivot = Vector(connection.shared_position)
            for obj, _connector_id in utils.connection_endpoints(connection):
                line_points.extend((obj.matrix_world.translation.copy(), pivot))
        _draw_lines(line_points, (0.2, 0.8, 1.0, 1.0), 2.0)


def _on_depsgraph_update(scene: bpy.types.Scene, depsgraph: Any) -> None:
    transforms.preserve_connections(scene)


def enable_draw_handler() -> None:
    """Install the viewport draw callback."""
    global _DRAW_HANDLER
    if _DRAW_HANDLER is None:
        _DRAW_HANDLER = bpy.types.SpaceView3D.draw_handler_add(
            draw_connectors,
            (),
            "WINDOW",
            "POST_VIEW",
        )
    utils.redraw_viewports()


def disable_draw_handler() -> None:
    """Remove the viewport draw callback."""
    global _DRAW_HANDLER
    if _DRAW_HANDLER is not None:
        bpy.types.SpaceView3D.draw_handler_remove(
            _DRAW_HANDLER,
            "WINDOW",
        )
        _DRAW_HANDLER = None
    set_preview(None, None)
    set_match_preview(None, None)
    set_cut_preview(None, None)


def enable_constraints() -> None:
    """Enable the active-connection transform constraint handler."""
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)


def disable_constraints() -> None:
    """Disable the active-connection transform constraint handler."""
    handlers = bpy.app.handlers.depsgraph_update_post
    if _on_depsgraph_update in handlers:
        handlers.remove(_on_depsgraph_update)


def register() -> None:
    """Register viewport drawing."""
    enable_draw_handler()


def unregister() -> None:
    """Unregister viewport drawing."""
    disable_draw_handler()
