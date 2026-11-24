"""Build the installable Kitbash Connector ZIP."""

import tomllib
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIRECTORY = PROJECT_ROOT / "kitbash_connector"
MANIFEST = PACKAGE_DIRECTORY / "blender_manifest.toml"
INCLUDED_FILES = (
    "__init__.py",
    "properties.py",
    "placement.py",
    "transforms.py",
    "utils.py",
    "visuals.py",
    "cutting.py",
    "operators.py",
    "panel.py",
    "blender_manifest.toml",
)


def output_path() -> Path:
    """Return the versioned archive path from the Blender manifest."""
    with MANIFEST.open("rb") as manifest_file:
        version = tomllib.load(manifest_file)["version"]
    return PROJECT_ROOT / f"kitbash_connector-{version}.zip"


def build() -> None:
    """Create a new versioned ZIP without replacing an existing release."""
    output = output_path()
    if output.exists():
        raise FileExistsError(
            f"{output.name} already exists. Increment the package version.",
        )
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        for filename in INCLUDED_FILES:
            source = PACKAGE_DIRECTORY / filename
            archive.write(source, Path("kitbash_connector") / filename)
        archive.write(PROJECT_ROOT / "README.md", "kitbash_connector/README.md")
        archive.write(PROJECT_ROOT / "LICENSE", "kitbash_connector/LICENSE")
    print(output)


if __name__ == "__main__":
    build()
