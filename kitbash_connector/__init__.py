"""Kitbash Connector Blender add-on."""

bl_info = {
    "name": "Kitbash Connector",
    "author": "Kitbash Connector contributors",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Kitbash Connector",
    "description": "Place surface anchors and assemble independent mesh objects",
    "category": "3D View",
}

from . import operators, panel, properties, visuals


MODULES = (operators, panel, properties, visuals)


def register() -> None:
    """Register all add-on classes, properties, and handlers."""
    for module in MODULES:
        module.register()
    visuals.enable_constraints()


def unregister() -> None:
    """Unregister all add-on classes, properties, and handlers."""
    visuals.disable_constraints()
    for module in reversed(MODULES):
        module.unregister()


if __name__ == "__main__":
    register()
