"""Operators implementing connector and connection workflows."""

from typing import Any, Optional

import bpy
from bpy.props import EnumProperty, FloatProperty
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


class KITBASH_OT_stick_parts(bpy.types.Operator):
    """Create and connect anchors through a guided viewport workflow."""

    bl_idname = "kitbash.stick_parts"
    bl_label = "Stick Parts Together"
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
        self._movable = context.active_object
        self._source_position = None
        self._source_normal = None
        self._camera_navigation = False
        visuals.set_preview(None, None)
        visuals.set_match_preview(None, None)
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set("CROSSHAIR")
        self._set_status(
            context,
            "Step 1: click where the moving part should connect.",
        )
        return {"RUNNING_MODAL"}

    def modal(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._finish(context)
            return {"CANCELLED"}
        if event.type == "MIDDLEMOUSE":
            self._camera_navigation = event.value == "PRESS"
            return {"PASS_THROUGH"}
        if self._camera_navigation and event.type == "MOUSEMOVE":
            return {"PASS_THROUGH"}
        if self._is_navigation_event(event):
            return {"PASS_THROUGH"}
        if event.type == "MOUSEMOVE":
            self._update_hover(context, event)
        elif event.type == "LEFTMOUSE" and event.value == "PRESS":
            if self._source_position is None:
                return self._choose_source(context, event)
            return self._choose_target(context, event)
        return {"RUNNING_MODAL"}

    @staticmethod
    def _is_navigation_event(event: bpy.types.Event) -> bool:
        return (
            event.type
            in {
                "WHEELUPMOUSE",
                "WHEELDOWNMOUSE",
                "TRACKPADPAN",
                "MOUSEROTATE",
                "NDOF_MOTION",
            }
            or event.type.startswith("NUMPAD_")
        )

    def _choose_source(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        hit = placement.raycast_surface(
            context,
            self._movable,
            (event.mouse_region_x, event.mouse_region_y),
        )
        if hit is None:
            self.report(
                {"WARNING"},
                "Click a visible face on the part that should move.",
            )
            return {"RUNNING_MODAL"}
        self._source_position, self._source_normal = hit
        visuals.set_preview(None, None)
        self._set_status(
            context,
            (
                f"Step 2: '{self._movable.name}' will move. "
                "Hover over another part and click a point."
            ),
        )
        return {"RUNNING_MODAL"}

    def _update_hover(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> None:
        mouse = (event.mouse_region_x, event.mouse_region_y)
        if self._source_position is None:
            hit = placement.raycast_surface(context, self._movable, mouse)
            visuals.set_preview(
                hit[0] if hit is not None else None,
                hit[1] if hit is not None else None,
            )
            return
        hit = placement.raycast_any_surface(
            context,
            mouse,
            excluded=self._movable,
        )
        if hit is None:
            visuals.set_preview(None, None)
            visuals.set_match_preview(None, None)
            return
        target, position, normal = hit
        selected = placement.connector_near_cursor(context, target, mouse)
        selected_in_use = False
        if selected is not None:
            position = utils.connector_world_position(target, selected)
            normal = utils.connector_world_normal(target, selected)
            selected_in_use = utils.connection_for(
                context.scene,
                target,
                selected.connector_id,
                active_only=True,
            ) is not None
        preview_matrix = transforms.aligned_matrix(
            self._movable.matrix_world,
            self._source_position,
            self._source_normal,
            position,
            normal,
            align_normals=True,
        )
        visuals.set_match_preview(
            target,
            selected,
            self._movable,
            None if selected_in_use else preview_matrix,
        )
        visuals.set_preview(
            position if selected is None else None,
            normal if selected is None else None,
        )

    def _choose_target(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        mouse = (event.mouse_region_x, event.mouse_region_y)
        hit = placement.raycast_any_surface(
            context,
            mouse,
            excluded=self._movable,
        )
        if hit is None:
            self.report({"WARNING"}, "Hover over a second mesh and try again.")
            return {"RUNNING_MODAL"}
        target, position, normal = hit
        target_connector = placement.connector_near_cursor(
            context,
            target,
            mouse,
        )
        if target_connector is not None and utils.connection_for(
            context.scene,
            target,
            target_connector.connector_id,
            active_only=True,
        ) is not None:
            self.report(
                {"WARNING"},
                "That connection point is already in use. Choose another.",
            )
            return {"RUNNING_MODAL"}
        settings = context.scene.kitbash_settings
        movable_connector = placement.add_connector(
            self._movable,
            self._source_position,
            self._source_normal,
            visual_size=settings.visual_size,
            snap_precision=settings.snap_precision,
        )
        if target_connector is None:
            target_connector = placement.add_connector(
                target,
                position,
                normal,
                visual_size=settings.visual_size,
                snap_precision=settings.snap_precision,
            )
        transforms.align_connector_pair(
            context.scene,
            target,
            target_connector,
            self._movable,
            movable_connector,
            align_normals=True,
        )
        self._finish(context)
        return {"FINISHED"}

    @staticmethod
    def _set_status(context: bpy.types.Context, message: str) -> None:
        context.workspace.status_text_set(message)
        context.area.header_text_set(message)

    def _finish(self, context: bpy.types.Context) -> None:
        visuals.set_preview(None, None)
        visuals.set_match_preview(None, None)
        context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)
        context.area.header_text_set(None)
        utils.redraw_viewports()


class KITBASH_OT_move_connector(bpy.types.Operator):
    """Move a connected anchor to another visible surface on its object."""

    bl_idname = "kitbash.move_connector"
    bl_label = "Move Connection Point"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        connection, _connector = utils.active_connection_endpoint(
            context.scene,
            context.active_object,
        )
        return connection is not None

    def invoke(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        self._object = context.active_object
        (
            self._connection,
            self._connector,
        ) = utils.active_connection_endpoint(
            context.scene,
            self._object,
        )
        self._camera_navigation = False
        active_for_object = [
            connection
            for connection in context.scene.kitbash_connections
            if connection.is_connected
            and (
                connection.object_a == self._object
                or connection.object_b == self._object
            )
        ]
        if len(active_for_object) > 1:
            self.report(
                {"WARNING"},
                "Disconnect the other connection before moving this point.",
            )
            return {"CANCELLED"}
        visuals.set_preview(None, None)
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set("CROSSHAIR")
        context.workspace.status_text_set(
            "Click another visible surface to move this connection point.",
        )
        return {"RUNNING_MODAL"}

    def modal(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        if event.type in {"RIGHTMOUSE", "ESC"}:
            self._finish(context)
            return {"CANCELLED"}
        if event.type == "MIDDLEMOUSE":
            self._camera_navigation = event.value == "PRESS"
            return {"PASS_THROUGH"}
        if self._camera_navigation and event.type == "MOUSEMOVE":
            return {"PASS_THROUGH"}
        if KITBASH_OT_stick_parts._is_navigation_event(event):
            return {"PASS_THROUGH"}
        if event.type == "MOUSEMOVE":
            hit = placement.raycast_surface(
                context,
                self._object,
                (event.mouse_region_x, event.mouse_region_y),
            )
            visuals.set_preview(
                hit[0] if hit is not None else None,
                hit[1] if hit is not None else None,
            )
        elif event.type == "LEFTMOUSE" and event.value == "PRESS":
            hit = placement.raycast_surface(
                context,
                self._object,
                (event.mouse_region_x, event.mouse_region_y),
            )
            if hit is None:
                self.report(
                    {"WARNING"},
                    "Click a visible face on the connected object.",
                )
                return {"RUNNING_MODAL"}
            transforms.move_connected_point(
                context.scene,
                self._connection,
                self._object,
                self._connector,
                hit[0],
                hit[1],
                snap_precision=context.scene.kitbash_settings.snap_precision,
            )
            self._finish(context)
            return {"FINISHED"}
        return {"RUNNING_MODAL"}

    @staticmethod
    def _finish(context: bpy.types.Context) -> None:
        visuals.set_preview(None, None)
        context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)
        utils.redraw_viewports()


class KITBASH_OT_remove_connector(bpy.types.Operator):
    """Remove the active connector and any relationship that uses it."""

    bl_idname = "kitbash.remove_connector"
    bl_label = "Remove Connector"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.active_object
        if obj is None:
            return False
        connection, _connector = utils.active_connection_endpoint(
            context.scene,
            obj,
        )
        return connection is not None or bool(obj.kitbash_connectors)

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        selected_connector = utils.active_connector(obj)
        connection, connected_connector = utils.active_connection_endpoint(
            context.scene,
            obj,
        )
        connector = (
            connected_connector
            if connection is not None
            else selected_connector
        )
        if connector is None:
            self.report({"ERROR"}, "Select a connector to remove.")
            return {"CANCELLED"}
        index = next(
            (
                index
                for index, candidate in enumerate(obj.kitbash_connectors)
                if candidate == connector
            ),
            -1,
        )
        if not 0 <= index < len(obj.kitbash_connectors):
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
        connection, _connector = utils.active_connection_endpoint(
            context.scene,
            context.active_object,
        )
        return connection is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        connection, _connector = utils.active_connection_endpoint(
            context.scene,
            context.active_object,
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
            (
                "NORMAL",
                "Rotation Dial",
                "Rotate around the connection direction",
            ),
        ],
        default="NORMAL",
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        connection, _connector = utils.active_connection_endpoint(
            context.scene,
            context.active_object,
        )
        return connection is not None

    def invoke(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        self._object = context.active_object
        _connection, connector = utils.active_connection_endpoint(
            context.scene,
            self._object,
        )
        self._connector = connector
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
        self._normal_axis = utils.connector_world_normal(
            self._object,
            self._connector,
        )
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
        if self.axis == "NORMAL":
            return Quaternion(
                self._normal_axis,
                delta.x * 0.01,
            )
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
        _connection, connector = utils.active_connection_endpoint(
            context.scene,
            context.active_object,
        )
        transforms.reset_object_rotation(
            context.scene,
            context.active_object,
            connector,
        )
        return {"FINISHED"}


class KITBASH_OT_rotation_dial(KITBASH_OT_rotate_connector):
    """Rotate a connected part around its connection with mouse movement."""

    bl_idname = "kitbash.rotation_dial"
    bl_label = "Rotation Dial"


class KITBASH_OT_rotate_step(bpy.types.Operator):
    """Rotate a connected part by a fixed angle around its connector."""

    bl_idname = "kitbash.rotate_step"
    bl_label = "Rotate Step"
    bl_options = {"REGISTER", "UNDO"}

    angle: FloatProperty(
        name="Angle",
        subtype="ANGLE",
        default=0.2617993877991494,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return KITBASH_OT_rotate_connector.poll(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        _connection, connector = utils.active_connection_endpoint(
            context.scene,
            obj,
        )
        pivot, _connection = transforms.pivot_for_object(
            context.scene,
            obj,
            connector,
        )
        transforms.rotate_connection_normal(obj, connector, pivot, self.angle)
        return {"FINISHED"}


class KITBASH_OT_flip_part(bpy.types.Operator):
    """Flip a connected part while preserving its shared attachment point."""

    bl_idname = "kitbash.flip_part"
    bl_label = "Flip"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return KITBASH_OT_rotate_connector.poll(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        _connection, connector = utils.active_connection_endpoint(
            context.scene,
            obj,
        )
        pivot, _connection = transforms.pivot_for_object(
            context.scene,
            obj,
            connector,
        )
        transforms.flip_connected_object(obj, connector, pivot)
        return {"FINISHED"}


CLASSES = (
    KITBASH_OT_place_connector,
    KITBASH_OT_stick_parts,
    KITBASH_OT_move_connector,
    KITBASH_OT_remove_connector,
    KITBASH_OT_toggle_connectors,
    KITBASH_OT_connect_selected,
    KITBASH_OT_disconnect,
    KITBASH_OT_reconnect,
    KITBASH_OT_rotate_connector,
    KITBASH_OT_rotation_dial,
    KITBASH_OT_reset_rotation,
    KITBASH_OT_rotate_step,
    KITBASH_OT_flip_part,
)


def register() -> None:
    """Register all add-on operators."""
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    """Unregister all add-on operators."""
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
