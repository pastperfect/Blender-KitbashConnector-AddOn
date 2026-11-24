# Kitbash Connector

Kitbash Connector is a modular Blender add-on for assembling separate mesh
objects with surface-mounted connection points. Connectors stay in object-local
space, so they follow the parent object's transforms without changing its mesh.

## Features

- Guided **Stick Parts Together** workflow with automatic connection points.
- Viewport ray-cast placement on the selected mesh.
- Local-space connector positions and inverse-transpose surface normals.
- Multiple connector points and multiple independent scene connections.
- Exact anchor alignment while keeping both Blender objects editable.
- Face-to-face normal alignment for guided assembly.
- Pivot-preserving rotation dial, 15/90 degree steps, flip, and depth controls.
- Active hinge constraints for ordinary object transforms.
- Disconnect, reconnect, and rotation reset.
- Viewport markers, normal previews, and connection lines.
- Undo support for add-on operations.

## Requirements

- Blender 4.2 or newer.
- Mesh objects. Other object types can remain in the scene but are not used as
  connector hosts.

## Installation

1. Download `kitbash_connector-1.1.5.zip`.
2. In Blender, open **Edit > Preferences > Get Extensions**.
3. Choose the menu's **Install from Disk** command and select the ZIP.
4. Enable **Kitbash Connector** if Blender does not enable it automatically.
5. Open the **3D Viewport > Sidebar (N) > Kitbash Connector** panel.

The package can also be installed from Blender's **Add-ons > Install from Disk**
view on supported versions.

## Quick Start

1. Select the mesh that should move.
2. Click **Stick Parts Together**.
3. Click a visible face on the moving part.
4. Hover over another mesh and click an available connection point.
5. If the target has no nearby point, clicking its surface creates one.
6. Use the **ADJUST** controls to rotate, flip, or push/pull the attached part.
   Use **Move Point** to reposition its connected anchor on the object's
   surface, or **Remove Point** to remove the anchor and relationship.
7. Use **Undo** at any time, or **Disconnect** to move the parts independently.

The existing manual connector placement and selected-anchor workflow remain
available in **ADVANCED**.

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
