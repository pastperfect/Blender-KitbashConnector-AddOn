"""Safe, non-destructive mesh separation and cut connector generation."""

import uuid
from dataclasses import dataclass
from typing import Any, Optional

import bmesh
import bpy
from mathutils import Vector

from . import placement


PLANE_TOLERANCE = 1.0e-5


class CutError(ValueError):
    """Describe a cut that cannot safely produce two mesh objects."""


@dataclass(frozen=True)
class CutResult:
    """Objects and connectors produced by a successful cut."""

    positive: bpy.types.Object
    negative: bpy.types.Object
    positive_connector: Any
    negative_connector: Any
    capped_positive: bool
    capped_negative: bool


def split_mesh(
    source: bpy.types.Object,
    plane_position: Vector,
    plane_normal: Vector,
    *,
    cap_surfaces: bool = True,
    preserve_original: bool = True,
    snap_precision: int = 6,
    visual_size: float = 0.08,
) -> CutResult:
    """Split a mesh with a plane, preserving the source by default."""
    plane_normal = plane_normal.normalized()
    if source.type != "MESH":
        raise CutError("Select a mesh object before using Cut Here.")
    if source.mode != "OBJECT":
        raise CutError("Return to Object Mode before using Cut Here.")
    source_connections = [
        connection
        for connection in bpy.context.scene.kitbash_connections
        if connection.object_a == source or connection.object_b == source
    ]
    if any(connection.is_connected for connection in source_connections):
        raise CutError(
            "Disconnect this object before cutting it.",
        )
    if not preserve_original and source_connections:
        raise CutError(
            "Keep Original must remain enabled for an object with saved "
            "connection records.",
        )

    evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    meshes: list[bpy.types.Mesh] = []
    created_objects: list[bpy.types.Object] = []
    local_plane = source.matrix_world.inverted() @ plane_position
    inverse_transpose = source.matrix_world.to_3x3().inverted().transposed()
    local_normal = inverse_transpose.inverted() @ plane_normal
    local_normal.normalize()
    try:
        if len(evaluated_mesh.vertices) < 3:
            raise CutError("The selected mesh does not contain enough geometry.")
        positive_mesh, positive_cap = _build_half(
            evaluated_mesh,
            local_plane,
            local_normal,
            positive=True,
            cap_surfaces=cap_surfaces,
        )
        meshes.append(positive_mesh)
        negative_mesh, negative_cap = _build_half(
            evaluated_mesh,
            local_plane,
            local_normal,
            positive=False,
            cap_surfaces=cap_surfaces,
        )
        meshes.append(negative_mesh)
        positive = _create_result_object(
            source,
            positive_mesh,
            f"{source.name} Cut +",
        )
        negative = _create_result_object(
            source,
            negative_mesh,
            f"{source.name} Cut -",
        )
        created_objects.extend((positive, negative))
        cut_position = _cut_centroid(
            positive_mesh,
            local_plane,
            local_normal,
        )
        world_cut_position = source.matrix_world @ cut_position
        _copy_existing_connectors(
            source,
            positive,
            negative,
            local_plane,
            local_normal,
        )
        positive_connector = placement.add_connector(
            positive,
            world_cut_position,
            plane_normal,
            visual_size=visual_size,
            snap_precision=snap_precision,
        )
        positive_connector.label = "Cut Point"
        negative_connector = placement.add_connector(
            negative,
            world_cut_position,
            -plane_normal,
            visual_size=visual_size,
            snap_precision=snap_precision,
        )
        negative_connector.label = "Cut Point"
        for obj in created_objects:
            for collection in source.users_collection:
                collection.objects.link(obj)
        if not preserve_original:
            bpy.data.objects.remove(source, do_unlink=True)
        else:
            source.hide_set(True)
            source.hide_render = True
        for selected in bpy.context.view_layer.objects:
            selected.select_set(False)
        positive.select_set(True)
        negative.select_set(True)
        bpy.context.view_layer.objects.active = positive
        bpy.context.view_layer.update()
        return CutResult(
            positive,
            negative,
            positive_connector,
            negative_connector,
            positive_cap,
            negative_cap,
        )
    except Exception:
        for obj in created_objects:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            if mesh.name in bpy.data.meshes:
                bpy.data.meshes.remove(mesh)
        raise
    finally:
        evaluated.to_mesh_clear()


def _build_half(
    evaluated_mesh: bpy.types.Mesh,
    plane_position: Vector,
    plane_normal: Vector,
    *,
    positive: bool,
    cap_surfaces: bool,
) -> tuple[bpy.types.Mesh, bool]:
    bm = bmesh.new()
    bm.from_mesh(evaluated_mesh)
    source_is_closed = all(len(edge.link_faces) == 2 for edge in bm.edges)
    try:
        result = bmesh.ops.bisect_plane(
            bm,
            geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
            plane_co=plane_position,
            plane_no=plane_normal,
            clear_outer=not positive,
            clear_inner=positive,
        )
        if not result["geom_cut"] or not bm.verts or not bm.faces:
            raise CutError(
                "The cutting plane did not divide the mesh into two parts.",
            )
        boundary_before_cap = _cut_boundary_edges(
            bm,
            plane_position,
            plane_normal,
        )
        if not boundary_before_cap:
            raise CutError(
                "The cutting plane produced no usable cut boundary.",
            )
        capped = False
        if cap_surfaces:
            bmesh.ops.holes_fill(
                bm,
                edges=boundary_before_cap,
                sides=0,
            )
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            capped = not _cut_boundary_edges(
                bm,
                plane_position,
                plane_normal,
            )
            if source_is_closed and not capped:
                raise CutError(
                    "The cut boundary is too complex to cap safely.",
                )
        bm.normal_update()
        mesh = bpy.data.meshes.new(
            f"{evaluated_mesh.name} {'+' if positive else '-'}",
        )
        bm.to_mesh(mesh)
        mesh.validate()
        mesh.update()
        return mesh, capped
    finally:
        bm.free()


def _cut_boundary_edges(
    bm: bmesh.types.BMesh,
    plane_position: Vector,
    plane_normal: Vector,
) -> list[bmesh.types.BMEdge]:
    return [
        edge
        for edge in bm.edges
        if edge.is_boundary
        and abs((edge.verts[0].co - plane_position).dot(plane_normal))
        <= PLANE_TOLERANCE
        and abs((edge.verts[1].co - plane_position).dot(plane_normal))
        <= PLANE_TOLERANCE
    ]


def _cut_centroid(
    mesh: bpy.types.Mesh,
    plane_position: Vector,
    plane_normal: Vector,
) -> Vector:
    points = [
        vertex.co.copy()
        for vertex in mesh.vertices
        if abs((vertex.co - plane_position).dot(plane_normal))
        <= PLANE_TOLERANCE
    ]
    if not points:
        raise CutError("The cut surface has no vertices for a connector.")
    return sum(points, Vector()) / len(points)


def _create_result_object(
    source: bpy.types.Object,
    mesh: bpy.types.Mesh,
    name: str,
) -> bpy.types.Object:
    obj = source.copy()
    obj.name = name
    obj.data = mesh
    obj.hide_set(False)
    obj.hide_render = False
    while obj.modifiers:
        obj.modifiers.remove(obj.modifiers[0])
    obj.kitbash_connectors.clear()
    return obj


def _copy_existing_connectors(
    source: bpy.types.Object,
    positive: bpy.types.Object,
    negative: bpy.types.Object,
    plane_position: Vector,
    plane_normal: Vector,
) -> None:
    for connector in source.kitbash_connectors:
        position = Vector(connector.local_position)
        target = positive if (
            (position - plane_position).dot(plane_normal) >= 0.0
        ) else negative
        copied = target.kitbash_connectors.add()
        copied.connector_id = uuid.uuid4().hex
        copied.label = connector.label
        copied.local_position = connector.local_position
        copied.local_normal = connector.local_normal
        copied.visual_size = connector.visual_size
        copied.connection_state = "Available"


def tilted_plane_normal(
    base_normal: Vector,
    view_right: Vector,
    angle: float,
    axis_rotation: float,
) -> Vector:
    """Return a plane normal tilted relative to a picked surface normal."""
    from mathutils import Quaternion

    normal = base_normal.normalized()
    tangent = view_right - normal * view_right.dot(normal)
    if tangent.length <= PLANE_TOLERANCE:
        tangent = normal.cross(Vector((0.0, 0.0, 1.0)))
        if tangent.length <= PLANE_TOLERANCE:
            tangent = normal.cross(Vector((1.0, 0.0, 0.0)))
    tangent.normalize()
    tangent = Quaternion(normal, axis_rotation) @ tangent
    return (Quaternion(tangent, angle) @ normal).normalized()
