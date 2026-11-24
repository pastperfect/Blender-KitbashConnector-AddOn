"""Build the installable Kitbash Connector ZIP."""

import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIRECTORY = PROJECT_ROOT / "kitbash_connector"
OUTPUT = PROJECT_ROOT / "kitbash_connector-1.0.0.zip"
INCLUDED_FILES = ("__init__.py", "properties.py", "placement.py",
                  "transforms.py", "utils.py", "visuals.py",
                  "operators.py", "panel.py", "blender_manifest.toml")


def build() -> None:
    """Create the versioned ZIP package."""
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename in INCLUDED_FILES:
            source = PACKAGE_DIRECTORY / filename
            archive.write(source, Path("kitbash_connector") / filename)
        archive.write(PROJECT_ROOT / "README.md", "kitbash_connector/README.md")
        archive.write(PROJECT_ROOT / "LICENSE", "kitbash_connector/LICENSE")
    print(OUTPUT)


if __name__ == "__main__":
    build()
