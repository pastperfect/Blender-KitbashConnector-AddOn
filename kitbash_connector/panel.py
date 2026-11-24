"""Kitbash Connector viewport panel and connector list."""

from typing import Any

import bpy

from . import utils


class KITBASH_UL_connectors(bpy.types.UIList):
    """Display named and connected connector points."""

    bl_idname = "KITBASH_UL_connectors"

    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: Any,
        item: Any,
        icon: int,
        active_data: Any,
        active_property: str,
        index: int = 0,
        flt_flag: int = 0,
    ) -> None:
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            split = layout.split(factor=0.68)
            split.label(text=item.label, icon="PINNED")
            split.label(text=item.connection_state)
        else:
            layout.alignment = "CENTER"
            layout.label(text="", icon="PINNED")


class KITBASH_PT_connector_panel(bpy.types.Panel):
    """Main add-on panel in the 3D Viewport sidebar."""

    bl_label = "Kitbash Connector"
    bl_idname = "KITBASH_PT_connector_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Kitbash Connector"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        obj = context.active_object
        settings = context.scene.kitbash_settings

        cut = layout.box()
        cut.label(text="CUT", icon="SCULPTMODE_HLT")
        cut.operator(
            "kitbash.cut_here",
            text="Cut Here",
            icon="MOD_BOOLEAN",
        )
        cut.prop(settings, "cut_preset")
        if settings.cut_preset == "CUSTOM":
            cut.prop(settings, "cut_angle")
        cut.prop(settings, "cut_cap_surfaces")
        cut.prop(settings, "cut_preserve_original")

        assemble = layout.box()
        assemble.label(text="ASSEMBLE", icon="CONSTRAINT")
        assemble.operator(
            "kitbash.stick_parts",
            text="Stick Parts Together",
            icon="LINKED",
        )
        assemble.operator(
            "kitbash.place_connector",
            text="Add Connection Point",
            icon="PIVOT_CURSOR",
        )
        assemble.label(text=self._connection_status(context), icon="INFO")

        connection = self._active_connection(context)
        adjust = layout.box()
        adjust.label(text="ADJUST", icon="ORIENTATION_GIMBAL")
        if connection is not None:
            rotation = adjust.row(align=True)
            for label, angle in (
                ("-90", -1.5707963267948966),
                ("-15", -0.2617993877991494),
                ("+15", 0.2617993877991494),
                ("+90", 1.5707963267948966),
            ):
                operator = rotation.operator(
                    "kitbash.rotate_step",
                    text=label,
                )
                operator.angle = angle
            row = adjust.row(align=True)
            row.operator("kitbash.flip_part", icon="FILE_REFRESH")
            row.operator("kitbash.disconnect", icon="UNLINKED")
            row = adjust.row(align=True)
            row.operator(
                "kitbash.move_connector",
                text="Move Point",
                icon="PIVOT_CURSOR",
            )
            row.operator(
                "kitbash.remove_connector",
                text="Remove Point",
                icon="REMOVE",
            )
            adjust.prop(connection, "depth_offset", slider=True)
            adjust.operator(
                "kitbash.rotation_dial",
                text="Rotation Dial",
                icon="TRACKBALL",
            )
        else:
            adjust.label(text="Connect parts to rotate or slide them.")
        adjust.operator("ed.undo", text="Undo", icon="LOOP_BACK")

        advanced = layout.box()
        advanced.label(text="ADVANCED", icon="PREFERENCES")
        advanced.operator(
            "kitbash.connect_selected",
            text="Connect Selected Anchors",
            icon="LINKED",
        )
        row = advanced.row(align=True)
        row.operator(
            "kitbash.remove_connector",
            text="Remove Point",
            icon="REMOVE",
        )
        row.operator("kitbash.disconnect", icon="UNLINKED")
        row.operator("kitbash.reconnect", icon="LINKED")
        advanced.operator(
            "kitbash.toggle_connectors",
            text=(
                "Hide Connectors"
                if settings.show_connectors
                else "Show Connectors"
            ),
            icon="HIDE_OFF" if settings.show_connectors else "HIDE_ON",
        )
        if obj is not None and obj.type == "MESH":
            advanced.template_list(
                "KITBASH_UL_connectors",
                "",
                obj,
                "kitbash_connectors",
                obj,
                "kitbash_active_connector",
                rows=3,
            )
        world_rotation = advanced.row(align=True)
        for axis in ("X", "Y", "Z"):
            operator = world_rotation.operator(
                "kitbash.rotate_connector",
                text=axis,
            )
            operator.axis = axis
        free_rotation = advanced.operator(
            "kitbash.rotate_connector",
            text="Free View Rotation",
            icon="TRACKBALL",
        )
        free_rotation.axis = "FREE"
        advanced.operator("kitbash.reset_rotation", icon="LOOP_BACK")
        advanced.prop(settings, "visual_size")
        advanced.prop(settings, "display_color")
        advanced.prop(settings, "snap_precision")
        advanced.prop(settings, "show_connection_lines")
        advanced.prop(settings, "show_surface_normals")
        advanced.prop(settings, "depth_limit")

    @staticmethod
    def _connection_status(context: bpy.types.Context) -> str:
        active_obj = context.active_object
        connector = utils.active_connector(active_obj)
        connection, connected = utils.active_connection_endpoint(
            context.scene,
            active_obj,
        )
        connector = connected or connector
        if connector is None:
            return "Status: select an object with a connector"
        if connection is None:
            connection = utils.connection_for(
                context.scene,
                active_obj,
                connector.connector_id,
            )
        if connection is None:
            return "Status: available"
        if connection.is_connected:
            return "Status: connected and constrained"
        return "Status: disconnected (reconnectable)"

    @staticmethod
    def _active_connection(context: bpy.types.Context) -> Any:
        connection, _connector = utils.active_connection_endpoint(
            context.scene,
            context.active_object,
        )
        return connection


CLASSES = (
    KITBASH_UL_connectors,
    KITBASH_PT_connector_panel,
)


def register() -> None:
    """Register panel classes."""
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    """Unregister panel classes."""
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
