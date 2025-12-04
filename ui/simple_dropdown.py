"""Simple dropdown widget used within projector settings."""

from typing import List, Optional

import nebulatk as ntk

from . import constants as ui_constants


class SimpleDropdown(ntk.Frame):
    """Minimal dropdown built from frames/labels toggled via show/hide."""

    def __init__(
        self,
        master,
        options: List[str],
        initial_value: str = "",
        width: int = 180,
        height: int = 30,
        command=None,
        password_entry=None,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            fill=ui_constants.DISABLED_COLOR,
            border=ui_constants.DISABLED_COLOR_HOVER,
            border_width=2,
        )
        self.password_entry = password_entry
        self.can_hover = True
        self.can_click = True
        self.command = self.toggle_options
        self.option_height = height
        self.options = options[:] if options else []
        self._ensure_initial_option(initial_value)
        self.value = initial_value or (self.options[0] if self.options else "")
        self._options_visible = False

        self.display_label = ntk.Label(
            self,
            text=self._format_value(self.value),
            font=("Arial", 11),
            justify="left",
            text_color=ui_constants.TEXT_COLOR,
            fill="#00000000",
        )
        self.display_label.place(x=8, y=2)
        self.display_label.can_click = True
        self.display_label.command = self.toggle_options

        self.caret_label = ntk.Label(
            self,
            text="v",
            font=("Arial", 12, "bold"),
            text_color=ui_constants.TEXT_COLOR,
            fill="#00000000",
        )
        self.caret_label.place(x=width - 20, y=2)
        self.caret_label.can_click = True
        self.caret_label.command = self.toggle_options

        self.options_frame = ntk.Frame(
            master,
            width=width,
            height=self.option_height * max(1, len(self.options)),
            fill=ui_constants.SETTINGS_PANEL_FILL,
            border=ui_constants.SETTINGS_BORDER_COLOR,
            border_width=2,
        )
        self.option_labels: List[ntk.Label] = []
        for idx, option in enumerate(self.options):
            label = ntk.Button(
                self.options_frame,
                text=self._format_value(option),
                font=("Arial", 10),
                justify="left",
                fill="#00000000",
                hover_fill=ui_constants.DISABLED_COLOR_HOVER,
                text_color=ui_constants.TEXT_COLOR,
                width=width - 16,
            )
            label.place(x=8, y=idx * self.option_height + 2)
            label.command = self._make_option_handler(option)
            self.option_labels.append(label)
        if not self.options:
            placeholder = ntk.Label(
                self.options_frame,
                text="No options",
                font=("Arial", 10),
                justify="left",
                fill="#00000000",
                text_color=ui_constants.TEXT_COLOR,
            )
            placeholder.place(x=8, y=6)
            self.option_labels.append(placeholder)
        self.options_frame.hide()

    def place(self, x=0, y=0):
        super().place(x=x, y=y)
        self._update_options_position()
        return self

    def _ensure_initial_option(self, initial_value: str):
        if initial_value and initial_value not in self.options:
            self.options.insert(0, initial_value)

    def _format_value(self, value: str) -> str:
        return value.replace("_", " ").title() if value else ""

    def _make_option_handler(self, option: str):
        def handler():
            self.set_value(option)
            self.hide_options()

        return handler

    def set_value(self, value: str):
        if value and value not in self.options:
            self.options.append(value)
        self.value = value
        self.display_label.configure(text=self._format_value(value))

    def get(self) -> str:
        return self.value

    def toggle_options(self):
        if self._options_visible:
            self.hide_options()
            if self.password_entry:
                self.password_entry.show()
        else:
            self._update_options_position()
            if self.password_entry:
                self.password_entry.hide()
            self.options_frame.show()
            self._options_visible = True

    def hide_options(self):
        self.options_frame.hide()
        self._options_visible = False
        if self.password_entry:
            self.password_entry.show()

    def _update_options_position(self):
        self.options_frame.place(x=self.x, y=self.y + self.height)
