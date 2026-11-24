"""Viewport drawing and dependency-graph connection constraints."""

from typing import Any, Optional

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from . import transforms, utils


_DRAW_HANDLER: Optional[Any] = None
_PREVIEW_POSITION: Optional[Vector] = None
_PREVIEW_NORMAL: Optional[Vector] = None


def set_preview(position: Optional[Vector], normal: Optional[Vector]) -> None:
    """Set the surface-placement preview point."""
    global _PREVIEW_POSITION, _PREVIEW_NORMAL
    _PREVIEW_POSITION = position.copy() if position is not None else None
    _PREVIEW_NORMAL = normal.copy() if normal is not None else None
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


def draw_connectors() -> None:
    """Draw connector points, normals, lines, and placement preview."""
    context = bpy.context
    scene = context.scene
    if scene is None or not hasattr(scene, "kitbash_settings"):
        return
    settings = scene.kitbash_settings
    if not settings.show_connectors:
        return

    marker_color = (*settings.display_color, 1.0)
    points: list[Vector] = []
    for obj in scene.objects:
        for connector in obj.kitbash_connectors:
            points.append(utils.connector_world_position(obj, connector))
            if settings.show_surface_normals:
                normal = utils.connector_world_normal(obj, connector)
                _draw_lines(
                    [
                        points[-1],
                        points[-1] + normal * settings.visual_size * 4.0,
                    ],
                    (0.2, 0.85, 1.0, 1.0),
                )
    _draw_points(points, marker_color, settings.visual_size)

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
