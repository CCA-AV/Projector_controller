import json
from pathlib import Path
from typing import Dict, List

from ui import create_projector_app


def list_projector_types() -> List[str]:
    """Return available projector module names from the projectors package."""
    projectors_dir = Path("projectors")
    if not projectors_dir.exists():
        return []
    types = []
    for file in projectors_dir.glob("*.py"):
        if file.name.startswith("_"):
            continue
        stem = file.stem
        if stem == "__init__":
            continue
        types.append(stem)
    return sorted(set(types))


def load_projectors_from_json(path: str = "data.json") -> List[Dict]:
    """Load persisted projector metadata."""
    if not Path(path).exists():
        import auto_discover

        data = auto_discover.auto_discover()
        auto_discover.save_discovery_results(data, "data.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Only use resolved projectors for full control
    return data.get("resolved", [])


def create_app(data_path: str = "data.json"):
    """Factory that wires loaded projector metadata into the UI app."""
    projector_defs = load_projectors_from_json(data_path)
    projector_types = list_projector_types()
    return create_projector_app(projector_defs, projector_types, data_path=data_path)


if __name__ == "__main__":
    app = create_app()
