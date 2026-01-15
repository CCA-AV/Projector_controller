"""High-level UI application builder for the projector controller."""

import contextlib
import json
from typing import Dict, List

import nebulatk as ntk

from modules.projector import Projector

from . import constants as ui_constants
from .projector_controller_frame import ProjectorControllerFrame


def create_projector_app(
    projector_defs: List[Dict],
    projector_types: List[str],
    data_path: str = "data.json",
):
    """
    Build the NebulaTK window populated with projector controller frames.

    Args:
        projector_defs: Projector metadata loaded from disk.
        projector_types: Available projector module names.
        data_path: JSON path used for persisting friendly names.
    """

    # Simple layout: vertical stack of controller frames
    frames = []
    frame_height = ui_constants.FRAME_HEIGHT
    window_height = max(frame_height * len(projector_defs), frame_height)
    window_width = ui_constants.WINDOW_WIDTH

    def _save_names_and_close():
        """
        Persist any edited projector names back to data.json before closing.
        """
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        resolved = data.get("resolved", [])

        # Update entries in order; if the JSON has fewer entries than frames,
        # update only what exists.
        for idx, frame in enumerate(frames):
            if idx >= len(resolved):
                break
            frame_data = frame.export_settings()
            resolved[idx].update(frame_data)

        data["resolved"] = resolved

        with contextlib.suppress(Exception):
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    window = ntk.Window(
        title="Projector Controller",
        width=window_width,
        height=window_height,
        closing_command=_save_names_and_close,
    )
    window.root.iconbitmap("images/icon.ico")
    window.updates_all = False

    background = ntk.Frame(
        window,
        fill=ui_constants.WINDOW_BACKGROUND,
        width=window_width,
        height=window_height,
    )
    background.place()

    for idx, meta in enumerate(projector_defs):
        print("creating frame for", meta["name"])
        ip = meta["ip"]
        proj_type = meta["projector_type"]
        username = meta.get("username")
        password = meta.get("password")

        proj = Projector(ip, proj_type, username=username, password=password)

        frame = ProjectorControllerFrame(
            background,
            proj,
            meta,
            projector_types=projector_types,
            width=ui_constants.FRAME_WIDTH,
            height=ui_constants.FRAME_HEIGHT,
        )
        frames.append(frame)
        window_height += (
            frame.height - ui_constants.FRAME_HEIGHT + ui_constants.FRAME_SPACING * 2
        )

        frame.place(
            x=ui_constants.FRAME_SPACING,
            y=ui_constants.FRAME_SPACING
            + idx * (ui_constants.FRAME_HEIGHT + ui_constants.FRAME_SPACING),
        )
        frame.show()
    background.configure(height=window_height)
    window.resize(window_width, window_height)
    return window
