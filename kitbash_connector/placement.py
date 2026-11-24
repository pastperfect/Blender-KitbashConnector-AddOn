"""Viewport ray casting and connector placement."""

import uuid
from typing import Any, Optional, Tuple

import bpy
from bpy_extras.view3d_utils import (
    location_3d_to_region_2d,
    region_2d_to_origin_3d,
    region_2d_to_vector_3d,
)
from mathutils import Vector

from . import utils


RayHit = Tuple[Vector, Vector]
ObjectRayHit = Tuple[bpy.types.Object, Vector, Vector]


def raycast_surface(
    context: bpy.types.Context,
    target: bpy.types.Object,
    mouse_position: tuple[int, int],
) -> Optional[RayHit]:
    """Ray cast the viewport and return a hit on the target mesh."""
    region = context.region
    region_data = context.region_data
    if region is None or region_data is None:
        return None
    origin = region_2d_to_origin_3d(
        region,
        region_data,
        mouse_position,
        clamp=1000.0,
    )
    direction = region_2d_to_vector_3d(
        region,
        region_data,
        mouse_position,
    )
    hit, location, normal, _, hit_object, _ = context.scene.ray_cast(
        context.evaluated_depsgraph_get(),
        origin,
        direction,
    )
    if not hit or hit_object is None:
        return None
    original = getattr(hit_object, "original", hit_object)
    if original != target:
        return None
    return location.copy(), normal.copy()


def raycast_any_surface(
    context: bpy.types.Context,
    mouse_position: tuple[int, int],
    *,
    excluded: Optional[bpy.types.Object] = None,
) -> Optional[ObjectRayHit]:
    """Ray cast the viewport and return the first mesh hit."""
    region = context.region
    region_data = context.region_data
    if region is None or region_data is None:
        return None
    origin = region_2d_to_origin_3d(
        region,
        region_data,
        mouse_position,
        clamp=1000.0,
    )
    direction = region_2d_to_vector_3d(
        region,
        region_data,
        mouse_position,
    )
    hit, location, normal, _, hit_object, _ = context.scene.ray_cast(
        context.evaluated_depsgraph_get(),
        origin,
        direction,
    )
    if not hit or hit_object is None:
        return None
    original = getattr(hit_object, "original", hit_object)
    if original.type != "MESH" or original == excluded:
        return None
    return original, location.copy(), normal.copy()


def connector_near_cursor(
    context: bpy.types.Context,
    obj: bpy.types.Object,
    mouse_position: tuple[int, int],
    *,
    available_only: bool = False,
    radius: float = 24.0,
) -> Optional[Any]:
    """Return the closest connector projected near a viewport cursor."""
    region = context.region
    region_data = context.region_data
    if region is None or region_data is None:
        return None
    mouse = Vector(mouse_position)
    nearest = None
    nearest_distance = radius
    for connector in obj.kitbash_connectors:
        if available_only and utils.connection_for(
            context.scene,
            obj,
            connector.connector_id,
            active_only=True,
        ) is not None:
            continue
        position_2d = location_3d_to_region_2d(
            region,
            region_data,
            utils.connector_world_position(obj, connector),
        )
        if position_2d is None:
            continue
        distance = (position_2d - mouse).length
        if distance < nearest_distance:
            nearest = connector
            nearest_distance = distance
    return nearest


def add_connector(
    obj: bpy.types.Object,
    world_position: Vector,
    world_normal: Vector,
    *,
    visual_size: float,
    snap_precision: int,
) -> Any:
    """Store a connector on an object in local coordinates."""
    local_position = utils.world_to_local_position(obj, world_position)
    local_normal = utils.world_to_local_normal(obj, world_normal)
    local_position = Vector(
        round(component, snap_precision) for component in local_position
    )
    connector = obj.kitbash_connectors.add()
    connector.connector_id = uuid.uuid4().hex
    connector.label = f"Connector {len(obj.kitbash_connectors):02d}"
    connector.local_position = local_position
    connector.local_normal = local_normal
    connector.visual_size = visual_size
    connector.connection_state = "Available"
    obj.kitbash_active_connector = len(obj.kitbash_connectors) - 1
    utils.redraw_viewports()
    return connector
