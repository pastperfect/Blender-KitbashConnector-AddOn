"""Operators implementing connector and connection workflows."""

from typing import Any, Optional

import bpy
from bpy.props import EnumProperty
from mathutils import Quaternion, Vector

from . import placement, transforms, utils, visuals


class KITBASH_OT_place_connector(bpy.types.Operator):
    """Place a connector on the active mesh under the mouse."""

    bl_idname = "kitbash.place_connector"
    bl_label = "Place Connector"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.active_object
        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
            and obj is not None
            and obj.type == "MESH"
        )

    def invoke(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        context.window_manager.modal_handler_add(self)
        self._target = context.active_object
        context.window.cursor_modal_set("CROSSHAIR")
        visuals.set_preview(None, None)
        return {"RUNNING_MODAL"}

    def modal(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._finish(context)
            return {"CANCELLED"}
        if event.type == "MOUSEMOVE":
            hit = placement.raycast_surface(
                context,
                self._target,
                (event.mouse_region_x, event.mouse_region_y),
            )
            if hit is None:
                visuals.set_preview(None, None)
            else:
                visuals.set_preview(*hit)
        elif event.type == "LEFTMOUSE" and event.value == "PRESS":
            hit = placement.raycast_surface(
                context,
                self._target,
                (event.mouse_region_x, event.mouse_region_y),
            )
            if hit is None:
                self.report(
                    {"WARNING"},
                    "The cursor must be over a face of the active mesh.",
                )
                return {"RUNNING_MODAL"}
            settings = context.scene.kitbash_settings
            placement.add_connector(
                self._target,
                hit[0],
                hit[1],
                visual_size=settings.visual_size,
                snap_precision=settings.snap_precision,
            )
            self._finish(context)
            return {"FINISHED"}
        return {"RUNNING_MODAL"}

    @staticmethod
    def _finish(context: bpy.types.Context) -> None:
        visuals.set_preview(None, None)
        context.window.cursor_modal_restore()


class KITBASH_OT_remove_connector(bpy.types.Operator):
    """Remove the active connector and any relationship that uses it."""

    bl_idname = "kitbash.remove_connector"
    bl_label = "Remove Connector"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return (
            context.active_object is not None
            and bool(context.active_object.kitbash_connectors)
        )

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        index = obj.kitbash_active_connector
        if index >= len(obj.kitbash_connectors):
            self.report({"ERROR"}, "Select a connector to remove.")
            return {"CANCELLED"}
        connector_id = obj.kitbash_connectors[index].connector_id
        scene_connections = context.scene.kitbash_connections
        for connection_index in range(len(scene_connections) - 1, -1, -1):
            connection = scene_connections[connection_index]
            uses_connector = (
                connection.object_a == obj
                and connection.connector_a_id == connector_id
            ) or (
                connection.object_b == obj
                and connection.connector_b_id == connector_id
            )
            if uses_connector:
                other_obj, other_id = next(
                    endpoint
                    for endpoint in utils.connection_endpoints(connection)
                    if endpoint != (obj, connector_id)
                )
                other_connector = utils.connector_by_id(other_obj, other_id)
                if other_connector is not None:
                    other_connector.connection_state = "Available"
                scene_connections.remove(connection_index)
        obj.kitbash_connectors.remove(index)
        obj.kitbash_active_connector = min(
            index,
            len(obj.kitbash_connectors) - 1,
        )
        utils.redraw_viewports()
        return {"FINISHED"}


class KITBASH_OT_toggle_connectors(bpy.types.Operator):
    """Show or hide viewport connector markers."""

    bl_idname = "kitbash.toggle_connectors"
    bl_label = "Show/Hide Connectors"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        settings = context.scene.kitbash_settings
        settings.show_connectors = not settings.show_connectors
        utils.redraw_viewports()
        return {"FINISHED"}


class _SelectedAnchorOperator(bpy.types.Operator):
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def _selected_anchors(
        cls,
        context: bpy.types.Context,
    ) -> Optional[tuple[bpy.types.Object, Any, bpy.types.Object, Any]]:
        selected = utils.selected_mesh_objects(context)
        if len(selected) != 2:
            return None
        obj_b = context.active_object
        if obj_b not in selected:
            return None
        obj_a = next(obj for obj in selected if obj != obj_b)
        connector_a = utils.active_connector(obj_a)
        connector_b = utils.active_connector(obj_b)
        if connector_a is None or connector_b is None:
            return None
        return obj_a, connector_a, obj_b, connector_b

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return cls._selected_anchors(context) is not None


class KITBASH_OT_connect_selected(_SelectedAnchorOperator):
    """Connect the active connectors on the two selected mesh objects."""

    bl_idname = "kitbash.connect_selected"
    bl_label = "Connect Selected Anchors"

    def execute(self, context: bpy.types.Context) -> set[str]:
        anchors = self._selected_anchors(context)
        if anchors is None:
            self.report({"ERROR"}, "Select two meshes with active connectors.")
            return {"CANCELLED"}
        try:
            transforms.align_connector_pair(context.scene, *anchors)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class KITBASH_OT_disconnect(bpy.types.Operator):
    """Disconnect the active anchor while retaining its relationship."""

    bl_idname = "kitbash.disconnect"
    bl_label = "Disconnect"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        connector = utils.active_connector(context.active_object)
        if connector is None:
            return False
        return utils.connection_for(
            context.scene,
            context.active_object,
            connector.connector_id,
            active_only=True,
        ) is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        connector = utils.active_connector(context.active_object)
        connection = utils.connection_for(
            context.scene,
            context.active_object,
            connector.connector_id,
            active_only=True,
        )
        transforms.disconnect_connection(context.scene, connection)
        return {"FINISHED"}


class KITBASH_OT_reconnect(_SelectedAnchorOperator):
    """Reconnect the selected connector pair at the first connector."""

    bl_idname = "kitbash.reconnect"
    bl_label = "Reconnect"

    def execute(self, context: bpy.types.Context) -> set[str]:
        anchors = self._selected_anchors(context)
        if anchors is None:
            self.report({"ERROR"}, "Select the two objects and their anchors.")
            return {"CANCELLED"}
        connection = utils.pair_connection(
            context.scene,
            anchors[0],
            anchors[1].connector_id,
            anchors[2],
            anchors[3].connector_id,
        )
        if connection is None:
            self.report({"ERROR"}, "No previous connection exists for this pair.")
            return {"CANCELLED"}
        try:
            transforms.reconnect_connection(context.scene, connection)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class KITBASH_OT_rotate_connector(bpy.types.Operator):
    """Rotate the active object about its connected anchor."""

    bl_idname = "kitbash.rotate_connector"
    bl_label = "Rotate Around Connector"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    axis: EnumProperty(
        items=[
            ("X", "Rotate X", "Rotate around the world X axis"),
            ("Y", "Rotate Y", "Rotate around the world Y axis"),
            ("Z", "Rotate Z", "Rotate around the world Z axis"),
            ("FREE", "Free Rotate", "Rotate freely in the current view"),
        ],
        default="FREE",
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        connector = utils.active_connector(context.active_object)
        if connector is None:
            return False
        return utils.connection_for(
            context.scene,
            context.active_object,
            connector.connector_id,
            active_only=True,
        ) is not None

    def invoke(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        connector = utils.active_connector(context.active_object)
        self._object = context.active_object
        self._matrix = self._object.matrix_world.copy()
        self._pivot, self._connection = transforms.pivot_for_object(
            context.scene,
            self._object,
            connector,
        )
        self._mouse_start = Vector(
            (event.mouse_region_x, event.mouse_region_y),
        )
        self._view_rotation = context.region_data.view_rotation.copy()
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set("SCROLL_XY")
        return {"RUNNING_MODAL"}

    def modal(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        if event.type == "MOUSEMOVE":
            delta = Vector(
                (event.mouse_region_x, event.mouse_region_y),
            ) - self._mouse_start
            rotation = self._rotation_from_delta(delta)
            transforms.rotate_about_connector(
                self._object,
                self._matrix,
                self._pivot,
                rotation,
            )
            return {"RUNNING_MODAL"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            context.window.cursor_modal_restore()
            utils.redraw_viewports()
            return {"FINISHED"}
        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._object.matrix_world = self._matrix
            context.window.cursor_modal_restore()
            utils.redraw_viewports()
            return {"CANCELLED"}
        return {"RUNNING_MODAL"}

    def _rotation_from_delta(self, delta: Vector) -> Quaternion:
        if self.axis != "FREE":
            vector = {
                "X": Vector((1.0, 0.0, 0.0)),
                "Y": Vector((0.0, 1.0, 0.0)),
                "Z": Vector((0.0, 0.0, 1.0)),
            }[self.axis]
            return Quaternion(vector, delta.x * 0.01)
        vertical_axis = self._view_rotation @ Vector((1.0, 0.0, 0.0))
        horizontal_axis = self._view_rotation @ Vector((0.0, 1.0, 0.0))
        return (
            Quaternion(vertical_axis, delta.y * 0.01)
            @ Quaternion(horizontal_axis, -delta.x * 0.01)
        )


class KITBASH_OT_reset_rotation(bpy.types.Operator):
    """Restore the active object's rotation at the shared connection point."""

    bl_idname = "kitbash.reset_rotation"
    bl_label = "Reset Rotation"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return KITBASH_OT_rotate_connector.poll(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        transforms.reset_object_rotation(
            context.scene,
            context.active_object,
            utils.active_connector(context.active_object),
        )
        return {"FINISHED"}


CLASSES = (
    KITBASH_OT_place_connector,
    KITBASH_OT_remove_connector,
    KITBASH_OT_toggle_connectors,
    KITBASH_OT_connect_selected,
    KITBASH_OT_disconnect,
    KITBASH_OT_reconnect,
    KITBASH_OT_rotate_connector,
    KITBASH_OT_reset_rotation,
)


def register() -> None:
    """Register all add-on operators."""
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    """Unregister all add-on operators."""
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
