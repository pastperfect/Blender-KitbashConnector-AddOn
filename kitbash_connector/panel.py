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

        placement = layout.box()
        placement.label(text="Connector Placement", icon="PIVOT_CURSOR")
        placement.operator(
            "kitbash.place_connector",
            text="Place Connector",
            icon="ADD",
        )
        placement.operator(
            "kitbash.remove_connector",
            text="Remove Connector",
            icon="REMOVE",
        )
        visibility = placement.operator(
            "kitbash.toggle_connectors",
            text="Hide Connectors" if settings.show_connectors else "Show Connectors",
            icon="HIDE_OFF" if settings.show_connectors else "HIDE_ON",
        )
        if obj is not None and obj.type == "MESH":
            placement.template_list(
                "KITBASH_UL_connectors",
                "",
                obj,
                "kitbash_connectors",
                obj,
                "kitbash_active_connector",
                rows=3,
            )

        management = layout.box()
        management.label(text="Connection Management", icon="CONSTRAINT")
        management.operator(
            "kitbash.connect_selected",
            text="Connect Selected Anchors",
            icon="LINKED",
        )
        row = management.row(align=True)
        row.operator("kitbash.disconnect", icon="UNLINKED")
        row.operator("kitbash.reconnect", icon="LINKED")
        management.label(
            text=self._connection_status(context),
            icon="INFO",
        )

        manipulation = layout.box()
        manipulation.label(text="Object Manipulation", icon="ORIENTATION_GIMBAL")
        row = manipulation.row(align=True)
        for axis in ("X", "Y", "Z"):
            operator = row.operator(
                "kitbash.rotate_connector",
                text=f"Rotate {axis}",
            )
            operator.axis = axis
        operator = manipulation.operator(
            "kitbash.rotate_connector",
            text="Free Rotate",
            icon="TRACKBALL",
        )
        operator.axis = "FREE"
        manipulation.operator(
            "kitbash.reset_rotation",
            icon="LOOP_BACK",
        )

        display = layout.box()
        display.label(text="Settings", icon="PREFERENCES")
        display.prop(settings, "visual_size")
        display.prop(settings, "display_color")
        display.prop(settings, "snap_precision")
        display.prop(settings, "show_connection_lines")
        display.prop(settings, "show_surface_normals")

    @staticmethod
    def _connection_status(context: bpy.types.Context) -> str:
        active_obj = context.active_object
        connector = utils.active_connector(active_obj)
        if connector is None:
            return "Status: select an active connector"
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
