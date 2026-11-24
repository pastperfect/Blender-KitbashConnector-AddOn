# Kitbash Connector

Kitbash Connector is a modular Blender add-on for assembling separate mesh
objects with surface-mounted connection points. Connectors stay in object-local
space, so they follow the parent object's transforms without changing its mesh.

## Features

- Viewport ray-cast placement on the selected mesh.
- Local-space connector positions and inverse-transpose surface normals.
- Multiple connector points and multiple independent scene connections.
- Exact anchor alignment while keeping both Blender objects editable.
- Pivot-preserving X, Y, Z, and free viewport rotation.
- Active hinge constraints for ordinary object transforms.
- Disconnect, reconnect, and rotation reset.
- Viewport markers, normal previews, and connection lines.
- Undo support for add-on operations.

## Requirements

- Blender 4.2 or newer.
- Mesh objects. Other object types can remain in the scene but are not used as
  connector hosts.

## Installation

1. Download `kitbash_connector-1.0.0.zip`.
2. In Blender, open **Edit > Preferences > Get Extensions**.
3. Choose the menu's **Install from Disk** command and select the ZIP.
4. Enable **Kitbash Connector** if Blender does not enable it automatically.
5. Open the **3D Viewport > Sidebar (N) > Kitbash Connector** panel.

The package can also be installed from Blender's **Add-ons > Install from Disk**
view on supported versions.

## Quick Start

1. Select a mesh and click **Place Connector**.
2. Hover over a visible face and left-click to confirm.
3. Select a second mesh, place another connector, and select both meshes.
4. The last selected object is the object that moves during connection.
5. Click **Connect Selected Anchors**.
6. Select either connected object and rotate with X, Y, Z, or Free Rotate.
7. Left-click to confirm a rotation or press Escape/right-click to cancel.
8. Use **Disconnect** before unrestricted independent movement, or
   **Reconnect** to restore the previously recorded pair.

See [docs/user-guide.md](docs/user-guide.md) for detailed controls and
limitations.

## Development

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" `
  --background --factory-startup --python-exit-code 1 `
  --python tests\blender_smoke.py
.\.venv\Scripts\python.exe tools\build_zip.py
```

The runtime has no third-party dependencies. Blender supplies `bpy`, `mathutils`,
`bpy_extras`, and `gpu`.
