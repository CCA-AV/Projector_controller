"""Reusable loading indicator context manager."""

from typing import Dict, Optional

import nebulatk as ntk


class LoadingIndicator:
    """
    Simple reference-counted loading indicator controller.
    Shows the provided label while one or more commands are active.
    """

    def __init__(self, label: ntk.Label, root, place_kwargs: Optional[Dict] = None):
        self.label = label
        self.root = root
        self._active = 0
        self._place_kwargs = place_kwargs or {}

    def __enter__(self):
        print("entering loading context")
        self._active += 1
        if self._active == 1:
            if self._place_kwargs:
                self.label.place(**self._place_kwargs)
            self.label.show()
            self.label.update()
            self.label.master.update()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._active > 0:
            self._active -= 1
        if self._active == 0:
            self.label.hide()
        return False
